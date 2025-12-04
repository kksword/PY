import os
from datetime import timedelta


class Config:
    # 基础配置，优先从环境变量读取，也提供默认值。
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

    # 数据库配置，指定SQLite数据库文件路径
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'switches.db')

    # SNMP配置
    SNMP_CONFIG = {
        'username': 'zabbix_secure',
        'auth_key': 'dxcz#123',
        'priv_key': 'dxcz#123',
        'auth_protocol': 'SHA',
        'priv_protocol': 'AES'
    }

    # 设备配置,嵌套字典
    SWITCHES = {
        'core_switch': {
            'ip': '192.168.254.254',
            'name': '核心交换机',
            'location': '机房',
            'snmp_version': '3'
        },
        'floor1_switch': {
            'ip': '192.168.254.14',
            'name': '十四楼汇聚',
            'location': '十四楼',
            'snmp_version': '3'
        },
        'floor2_switch': {
            'ip': '192.168.254.10',
            'name': '十楼汇聚',
            'location': '十楼',
            'snmp_version': '3'
        },
        'floor3_switch': {
            'ip': '192.168.254.9',
            'name': '九楼汇聚',
            'location': '九楼',
            'snmp_version': '3'
        },
        'floor4_switch': {
            'ip': '192.168.254.8',
            'name': '八楼汇聚',
            'location': '八楼',
            'snmp_version': '3'
        }
    }

    # 阈值配置
    THRESHOLDS = {
        'broadcast_threshold': 1000,  # 广播包阈值(包/秒)
        'error_threshold': 50,  # 错误包阈值
        'idle_duration': 30,  # 闲置端口判定时间(天)
    }

    # 采集间隔(秒)，5分钟
    COLLECTION_INTERVAL = 300