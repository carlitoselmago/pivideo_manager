from piVideoManager import piVideoManager

masterip="192.168.5.123"
devices=[]

manager = piVideoManager(masterip,devices)

online_devices = manager.scan_ip_range('192.168.5.0/24')
print("Online devices:", online_devices)