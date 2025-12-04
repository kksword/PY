from netmiko import ConnectHandler
import time
from config import Config

#该模块主要是一些自动化操作，包括建立SSH连接函数、关闭指定端口函数、启用指定端口函数
class SwitchOperator:
    def __init__(self, config):
        self.config = config #导入app实例的相关配置
    #针对某个交换价建立SSH连接
    def get_connection(self, switch_ip):
        """建立设备连接"""
        device_params = {
            'device_type': 'cisco_ios',  # 根据实际设备类型调整
            'ip': switch_ip,
            'username': 'your-ssh-username',  # 需要配置SSH凭据
            'password': 'your-ssh-password',
            'secret': 'your-enable-password',  # 如果需要
            'timeout': 30
        }

        try:
            connection = ConnectHandler(**device_params)
            return connection
        except Exception as e:
            print(f"连接设备 {switch_ip} 失败: {e}")
            return None
    #针对某个交换机的指定端口进行shutdown操作
    def shutdown_port(self, switch_ip, port_name):
        """关闭指定端口"""
        connection = self.get_connection(switch_ip)
        if not connection:
            return False, "连接失败"

        try:
            # 进入特权模式
            connection.enable()

            # 配置命令
            commands = [
                f"interface {port_name}",
                "shutdown",
                "exit"
            ]

            output = connection.send_config_set(commands)

            # 保存配置（如果需要）
            # connection.send_command("write memory")

            connection.disconnect()
            return True, "端口关闭成功"

        except Exception as e:
            return False, f"操作失败: {e}"
    #启用某个交换机的指定端口
    def enable_port(self, switch_ip, port_name):
        """启用指定端口"""
        connection = self.get_connection(switch_ip)
        if not connection:
            return False, "连接失败"

        try:
            connection.enable()

            commands = [
                f"interface {port_name}",
                "no shutdown",
                "exit"
            ]

            output = connection.send_config_set(commands)
            connection.disconnect()
            return True, "端口启用成功"

        except Exception as e:
            return False, f"操作失败: {e}"