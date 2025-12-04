from pysnmp.hlapi import *

# 测试导入是否成功
print("正在测试 pysnmp 导入...")

# 测试基本组件
components = [
    'getCmd', 'nextCmd', 'SnmpEngine', 'UsmUserData',
    'UdpTransportTarget', 'ContextData', 'ObjectType', 'ObjectIdentity'
]

for comp in components:
    try:
        globals()[comp]
        print(f"✓ {comp} 导入成功")
    except:
        print(f"✗ {comp} 导入失败")

# 测试协议导入
try:
    from pysnmp.hlapi import usmHMACSHAAuthProtocol, usmAesCfb128Protocol

    print("✓ SNMP V3 协议导入成功")
except ImportError as e:
    print(f"✗ SNMP V3 协议导入失败: {e}")
    print("尝试备用导入方式...")

    try:
        # 备用导入方式
        from pysnmp.proto.secmod.rfc3414.auth import hmacsha
        from pysnmp.proto.secmod.rfc3414.priv import aes

        usmHMACSHAAuthProtocol = hmacsha.HmacSha
        usmAesCfb128Protocol = aes.Aes
        print("✓ 使用备用方式导入成功")
    except Exception as e2:
        print(f"✗ 备用导入也失败: {e2}")

print("\n测试完成！")