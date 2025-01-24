from pivideo_manager import PiVideoManager



manager = PiVideoManager()

# Update setup details
manager.update_setup("Gofre")
print(manager.get_setup_info())

# Scan IP range and add devices
manager.scan_ip_range('192.168.100.0/24')

# Get all discovered devices
devices = manager.get_all_devices()
print(devices)

# Connect to devices
manager.connect_to_devices()

# Set master device
manager.set_master_device('192.168.100.10')

# Close connections
manager.close_connections()

"""

# master ip
masterip= "192.168.5.180"


# Create an instance of RaspberryPiManager
manager = PiVideoManager()

# Connect to all devices
manager.connect_to_devices()

# Collect and store all device information
manager.collect_device_info()

# Retrieve and display all device info
device_info = manager.get_all_device_info()
for name, info in device_info.items():
    print(f"\nDevice: {name}")
    for key, value in info.items():
        print(f"  {key}: {value}")

# Example: Execute a custom command on a specific device
#output = manager.execute_command("raspberry1", "uname -a")
#print(f"\nCommand output from raspberry1: {output}")

# Close all connections
manager.close_connections()

"""