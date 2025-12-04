from flask import Flask, render_template, jsonify, request
from config import Config
from models import SwitchMonitor
from snmp_collector import SNMPCollector
from netmiko_operator import SwitchOperator
import threading
import time
import json
from datetime import datetime, timedelta

app = Flask(__name__)  #flask类实例化为app
app.config.from_object(Config) #调用config模块对app实例进行配置

# 初始化组件，将SwitchMonitor类实例化，传入数据库路径实例属性，调用models模块的SwitchMonitor类创建监控系统的SQLite数据库结构
monitor = SwitchMonitor(Config.DATABASE_PATH)
#调用snmp_collector模块的SNMPCollector类，将其实例化，并导入app实例的SNMP配置
snmp_collector = SNMPCollector(Config)
#调用netmiko_operator模块的SwitchOperator类，将其实例化，并导入app实例的配置
switch_operator = SwitchOperator(Config)

# 全局状态
current_status = {}

#采集数据业务逻辑
def collect_data():
    """定时采集数据，通过遍历配置项所配置的交换机"""
    while True:
        try:
            #获取SWITCHES配置项，通过items()方法获取字典的键值对，switch_key接收字典的键，switch_info接收字典的值(嵌套字典)
            for switch_key, switch_info in app.config['SWITCHES'].items():
                print(f"采集 {switch_info['name']} 数据...") #获取嵌套字典中name键所对应的值，例如：采集核心交换机数据...
                #通过switch_info()获得各个设备的IP
                # 获取端口数据
                ports = snmp_collector.get_switch_ports(switch_info['ip'])

                # 保存到数据库
                monitor.save_port_data(switch_info['ip'], ports)

                # 分析状态并触发告警
                analyze_port_status(switch_info['ip'], ports)

                # 更新全局状态
                current_status[switch_key] = {
                    'name': switch_info['name'],
                    'location': switch_info['location'],
                    'ports': ports,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            print("数据采集完成")

        except Exception as e:
            print(f"数据采集错误: {e}")

        # 等待下次采集
        time.sleep(app.config['COLLECTION_INTERVAL'])

#端口状态分析函数
def analyze_port_status(switch_ip, ports):
    """分析端口状态并触发告警"""
    conn = monitor.db.get_connection()
    cursor = conn.cursor()

    for port in ports:
        # 检查广播包激增，向数据库的报警表中提交数据
        if port['in_broadcast_pkts'] > app.config['THRESHOLDS']['broadcast_threshold']:
            cursor.execute('''
                INSERT INTO alerts (switch_id, port_index, alert_type, description, severity)
                SELECT id, ?, 'broadcast_storm', '广播包激增，疑似环路风险', 'high'
                FROM switches WHERE ip = ?
            ''', (port['index'], switch_ip))

        # 检查错误包过多，向数据库中的报警表提交数据
        if port['in_errors'] + port['out_errors'] > app.config['THRESHOLDS']['error_threshold']:
            cursor.execute('''
                INSERT INTO alerts (switch_id, port_index, alert_type, description, severity)
                SELECT id, ?, 'high_errors', '错误包过多', 'medium'
                FROM switches WHERE ip = ?
            ''', (port['index'], switch_ip))

    conn.commit() #数据库提交
    conn.close() #关闭数据库连接


# app.py - 添加这些路由

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/switch_status')
def get_switch_status():
    """获取所有交换机状态"""
    return jsonify(current_status)


@app.route('/api/port_heatmap')
def get_port_heatmap():
    """获取端口热力图数据"""
    heatmap_data = []

    for switch_key, switch_data in current_status.items():
        for port in switch_data.get('ports', []):
            # 计算端口健康度得分
            score = calculate_port_score(port)

            heatmap_data.append({
                'switch': switch_data['name'],
                'port': port['name'],
                'status': port['oper_status'],
                'score': score,
                'errors': port['in_errors'] + port['out_errors'],
                'broadcast': port['in_broadcast_pkts'] + port['out_broadcast_pkts']
            })

    return jsonify(heatmap_data)


@app.route('/api/alerts')
def get_alerts():
    """获取告警信息"""
    try:
        conn = monitor.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT a.*, s.name as switch_name, s.ip as switch_ip 
            FROM alerts a 
            JOIN switches s ON a.switch_id = s.id 
            WHERE a.status = 'active'
            ORDER BY a.created_at DESC
            LIMIT 20
        ''')

        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'id': row[0],
                'switch': row[8],  # switch_name
                'port': row[2],  # port_index
                'type': row[3],  # alert_type
                'description': row[4],  # description
                'severity': row[5],  # severity
                'created_at': row[6]  # created_at
            })

        conn.close()
        return jsonify(alerts)
    except Exception as e:
        print(f"获取告警失败: {e}")
        return jsonify([])


@app.route('/api/operations', methods=['POST'])
def execute_operation():
    """执行自动化操作"""
    try:
        data = request.json
        switch_ip = data.get('switch_ip')
        port_name = data.get('port_name')
        operation = data.get('operation')

        if not all([switch_ip, port_name, operation]):
            return jsonify({'success': False, 'message': '缺少必要参数'})

        if operation == 'shutdown':
            success, message = switch_operator.shutdown_port(switch_ip, port_name)
        elif operation == 'enable':
            success, message = switch_operator.enable_port(switch_ip, port_name)
        else:
            success, message = False, "未知操作"

        # 记录操作到数据库
        if success:
            conn = monitor.db.get_connection()
            cursor = conn.cursor()

            # 查找交换机ID
            cursor.execute("SELECT id FROM switches WHERE ip = ?", (switch_ip,))
            switch = cursor.fetchone()
            if switch:
                cursor.execute('''
                    INSERT INTO operations (switch_id, port_index, operation_type, command, result)
                    VALUES (?, ?, ?, ?, ?)
                ''', (switch[0], port_name, operation, f"端口{operation}", message))
                conn.commit()

            conn.close()

        return jsonify({'success': success, 'message': message})

    except Exception as e:
        print(f"操作失败: {e}")
        return jsonify({'success': False, 'message': str(e)})


def calculate_port_score(port):
    """计算端口健康度得分"""
    score = 100

    # 端口状态
    if port['oper_status'] == 'down':
        score -= 40

    # 错误包
    error_count = port['in_errors'] + port['out_errors']
    if error_count > 100:
        score -= 30
    elif error_count > 50:
        score -= 15
    elif error_count > 10:
        score -= 5

    # 广播包
    broadcast_count = port['in_broadcast_pkts'] + port['out_broadcast_pkts']
    if broadcast_count > 1000:
        score -= 30
    elif broadcast_count > 500:
        score -= 15
    elif broadcast_count > 100:
        score -= 5

    return max(0, min(100, score))


if __name__ == '__main__':
    # 启动后台数据采集线程
    collector_thread = threading.Thread(target=collect_data, daemon=True)
    collector_thread.start()

    app.run(debug=True, host='0.0.0.0', port=5000)