from pivideo_manager import PiVideoManager



manager = PiVideoManager()

online_devices = manager.scan_ip_range('192.168.5.0/24')
print("Online devices:", online_devices)