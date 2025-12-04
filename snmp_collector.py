from pysnmp.hlapi import *
import time
from datetime import datetime
from config import Config


class SNMPCollector:
    def __init__(self, config):
        self.config = config #导入app实例的字典配置表
        self.snmp_config = config.SNMP_CONFIG #导入app实例的SNMP配置
    #target目标IP，OID(对象标识符)用于唯一标识SNMP管理信息库(MIB)中的特定对象
    def snmp_get(self, target, oid):
        """执行SNMP GET操作，查询某个特定值，返会次数一次"""
        try:
            #errorIndication:本地错误提示(网络问题、超时等),errorStatus:SNMP代理返回的错误状态
            #errorIndex:错误发生的位置索引、varBinds:实际的SNMP数据结果(变量绑定列表)
            #getCmd()的参数为对象实例，这是内联创建方式，也可以为每个实例赋值给某个变量，以变量名为实例名带入到getCmd()做参数
            #getCmd()返回生成器对象，通过next()迭代器返回一个四值元组，并通过元组解包方式赋值给四个变量
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    SnmpEngine(), #创建SNMP引擎实例
                    UsmUserData(
                        self.snmp_config['username'],
                        self.snmp_config['auth_key'],
                        self.snmp_config['priv_key'],
                        authProtocol=usmHMACSHAAuthProtocol,
                        privProtocol=usmAesCfb128Protocol
                    ), #SNMPv3用户认证信息，包含用户名、认证秘钥、加密密钥、所用的认证协议和加密协议，config模块有配置
                    UdpTransportTarget((target, 161)), #目标设备，即设备IP和端口
                    ContextData(), #SNMP参数上下文
                    ObjectType(ObjectIdentity(oid)) #要查询的OID，即所要查的设备的信息内容
                )
            )
            #针对返回错误，输出字符提示，若无错误，则返回获得的数据
            if error_indication:
                print(f"SNMP Error: {error_indication}")
                return None
            elif error_status:
                print(f"SNMP Error: {error_status}")
                return None
            else:
                for var_bind in var_binds:
                    return var_bind[1]
        except Exception as e: #针对可能抛出的异常
            print(f"SNMP Exception: {e}")
            return None
    #与snmp_get()相似，不过snmp_walk针对的是多个值的遍历
    def snmp_walk(self, target, oid):
        """执行SNMP WALK操作，遍历多个值，返回次数多次"""
        results = []
        try:
            #通过for循环遍历查询所要查询的设备信息，通过lexicographicMode=False控制nextCmd遍历的停止条件
            for (error_indication, error_status, error_index, var_binds) in nextCmd(
                    SnmpEngine(),
                    UsmUserData(
                        self.snmp_config['username'],
                        self.snmp_config['auth_key'],
                        self.snmp_config['priv_key'],
                        authProtocol=usmHMACSHAAuthProtocol,
                        privProtocol=usmAesCfb128Protocol
                    ),
                    UdpTransportTarget((target, 161)),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid)),
                    lexicographicMode=False #默认值，当遍历到不属于同一颗子树的OID时自动停止
            ):
                if error_indication:
                    print(f"SNMP Walk Error: {error_indication}")
                    break
                elif error_status:
                    print(f"SNMP Walk Error: {error_status}")
                    break
                else:
                    for var_bind in var_binds:
                        results.append(var_bind)
        except Exception as e:
            print(f"SNMP Walk Exception: {e}")

        return results

    def get_switch_ports(self, switch_ip):
        """获取交换机端口信息"""
        ports = []

        # OID字典定义，即所要查询交换机的对象信息，通过SNMP的表格结构，定义基础OID，nextCmd()会自动遍历表格中OID
        OIDS = {
            'if_index': '1.3.6.1.2.1.2.2.1.1', #接口索引，每个接口的唯一编号，唯一标识
            'if_name': '1.3.6.1.2.1.31.1.1.1.1', #接口名称，可读的接口名称，例如GE0/0/1,eth0,VLAN10等
            'if_admin_status': '1.3.6.1.2.1.2.2.1.7', #管理状态，UP或者DOWN，管理员设置的接口状态
            'if_oper_status': '1.3.6.1.2.1.2.2.1.8', #操作状态，接口实际运行状态
            'if_in_errors': '1.3.6.1.2.1.2.2.1.14', #输入错误数，即接受数据包时的错误计数
            'if_out_errors': '1.3.6.1.2.1.2.2.1.20', #输出错误数，即发送数据包时的错误计数
            'if_in_broadcast_pkts': '1.3.6.1.2.1.31.1.1.1.9', #输入广播包数，即接收的广播包数量
            'if_out_broadcast_pkts': '1.3.6.1.2.1.31.1.1.1.13', #输出广播包数，即发送的广播包数量
            'if_last_change': '1.3.6.1.2.1.2.2.1.9' #最后状态变化时间，即接口状态最近一次变化时间
        }

        # 获取端口索引，通过一个端口的基础OID，根据表格结构遍历所有端口的信息。
        port_indexes = self.snmp_walk(switch_ip, OIDS['if_index'])

        for index_oid, port_index in port_indexes:
            port_index = int(port_index)

            # 跳过非物理端口
            if port_index > 1000:  # 根据实际情况调整
                continue
            #下面字典中的键值对中的值的用法是典型的"SNMP OID构造+回退默认值"的写法，即值通过函数调用获得
            #snmp_get()有两个参数，其一为switch_ip,另一参数为f-string格式化字符串
            #OIDS['if_name']:取出键'if_name'对应的值，这是一个基础的OID字符串，例如：1.3.6.1.2.1.31.1.1.1.1
            #port_index之前for循环获得的端口索引值，例如：24
            #OIDS['if_name'].port_index组合起来即为：1.3.6.1.2.1.31.1.1.1.1.24
            #在snmp中，要获取具体某个端口的名称，必须在基础OID后面追加该端口的索引，即用.连接，下面字典中有很多类似的用法
            port_data = {
                'index': port_index,
                'name': self.snmp_get(switch_ip, f"{OIDS['if_name']}.{port_index}") or f"Port{port_index}",
                'admin_status': self.get_status_text(
                    self.snmp_get(switch_ip, f"{OIDS['if_admin_status']}.{port_index}")
                ),#将查询到的管理状态转换为可读形式然后作为该端口数据中键'admin_status'的值
                'oper_status': self.get_status_text(
                    self.snmp_get(switch_ip, f"{OIDS['if_oper_status']}.{port_index}")
                ),#将查询到的操作状态转换为可读形式然后作为该端口数据中键'oper_status'的值
                'in_errors': int(self.snmp_get(switch_ip, f"{OIDS['if_in_errors']}.{port_index}") or 0),
                'out_errors': int(self.snmp_get(switch_ip, f"{OIDS['if_out_errors']}.{port_index}") or 0),
                'in_broadcast_pkts': int(self.snmp_get(switch_ip, f"{OIDS['if_in_broadcast_pkts']}.{port_index}") or 0),
                'out_broadcast_pkts': int(
                    self.snmp_get(switch_ip, f"{OIDS['if_out_broadcast_pkts']}.{port_index}") or 0),
                'last_change': datetime.now()
            }

            ports.append(port_data) #将每次遍历所得的端口数据添加到ports中

        return ports #返回遍历查询的端口数据
    #将SNMP查询返回的数字状态码转换为可读的文本描述，供get_switch_ports()调用
    def get_status_text(self, status_code):
        """将状态代码转换为文本"""
        status_map = {
            1: 'up',
            2: 'down',
            3: 'testing'
        }
        return status_map.get(int(status_code or 1), 'unknown')