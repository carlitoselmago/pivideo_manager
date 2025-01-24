from piVideoManager import piVideoManager

# master ip
masterip= "192.168.5.180"
['192.168.5.1', '192.168.5.180', '192.168.5.208', '192.168.5.224']
"""


    {"name": "RASPI1", "ip": "192.168.10.181"},
    
    {"name": "RASPI3", "ip": "192.168.10.186"},
    {"name": "RASPI5", "ip": "192.168.10.182"},
    {"name": "RASPI9", "ip": "192.168.10.245"},
      
"""

# List of Raspberry Pi devices
devices = [
    {"name": "RASPI1", "ip": "192.168.5.180"},
    {"name": "RASPI8", "ip": "192.168.5.208"},
    {"name": "RASPI", "ip": "192.168.5.224"},
 
]

# Create an instance of RaspberryPiManager
manager = piVideoManager(masterip,devices)

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