import paramiko
import time
import platform
import ipaddress
import subprocess

class piVideoManager:

    username = "pi"
    password = "raspberry"

    def __init__(self, masterip,devices):
        """
        Initialize the RaspberryPiManager with a list of devices.
        Each device should be a dictionary containing 'name', 'ip', 'username', and 'password'.
        """
        self.masterip=masterip
        self.devices = devices
        self.connections = {}
        self.device_info = {}

    def connect_to_devices(self):
        """Establish SSH connections to all devices and store them."""
        for device in self.devices:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    hostname=device["ip"],
                    username=self.username,
                    password=self.password,
                    timeout=10
                )
                self.connections[device["name"]] = client
                print(f"Connected to {device['name']} ({device['ip']})")
            except Exception as e:
                print(f"Failed to connect to {device['name']} ({device['ip']}): {e}")

    def get_temperature(self, client):
        """Retrieve the CPU temperature from the Raspberry Pi."""
        try:
            stdin, stdout, stderr = client.exec_command("vcgencmd measure_temp")
            output = stdout.read().decode().strip()
            return output.split('=')[1] if output else "Unknown"
        except Exception as e:
            return f"Error: {e}"

    def get_raspi_model(self, client):
        """Retrieve the Raspberry Pi model."""
        try:
            stdin, stdout, stderr = client.exec_command("cat /proc/device-tree/model")
            return stdout.read().decode().strip() or "Unknown model"
        except Exception as e:
            return f"Error: {e}"

    def get_ram_size(self, client):
        """Retrieve the total RAM size in MB."""
        try:
            stdin, stdout, stderr = client.exec_command("free -m | awk '/^Mem:/ {print $2}'")
            return f"{stdout.read().decode().strip()} MB" if stdout else "Unknown RAM"
        except Exception as e:
            return f"Error: {e}"

    def get_mac_address(self, client):
        """Retrieve the MAC address of the Raspberry Pi."""
        try:
            stdin, stdout, stderr = client.exec_command("cat /sys/class/net/eth0/address")
            return stdout.read().decode().strip() or "Unknown MAC"
        except Exception as e:
            return f"Error: {e}"
    
    def get_lag(self, client):
        """Retrieve the lag using ping to the master player."""
        try:
            # Send a single ping request with a 1-second timeout
            stdin, stdout, stderr = client.exec_command(f"ping -c 1 -W 1 {self.masterip}")
            output = stdout.read().decode().strip()

            # Extract the ping time from the output
            if "time=" in output:
                lag = output.split("time=")[-1].split(" ")[0]
                return f"{lag} ms"
            else:
                return "Ping failed or no response"
        except Exception as e:
            return f"Error: {e}"
        
    import time

    def show_txt_message_on_screen(self, client, msg):
        """
        Shows the provided message on the screen of all connected devices using ffmpeg and omxplayer.
        """

        # Construct the ffmpeg command
        escaped_msg = msg.replace(':', r'\:').replace('\n', r'\\ ')

        seconds = 10
        command = (
            f'ffmpeg -y -f lavfi -i "color=c=black:s=1280x720,drawtext=fontfile=/usr/share/fonts/FreeSans.ttf:fontsize=48:text=\'{escaped_msg}\':fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2\" -t {seconds} -c:v libx264 -pix_fmt yuv420p msg.mp4 && omxplayer msg.mp4 --layer 2'
        )


        # Execute the command on the device
        try:
            stdin, stdout, stderr = client.exec_command(command)
            
            # Wait for the command to complete
            while not stdout.channel.exit_status_ready():
                time.sleep(1)

            exit_status = stdout.channel.recv_exit_status()  # Blocks until command is done
            
            if exit_status == 0:
                print("Message displayed successfully.")
            else:
                error_msg = stderr.read().decode()
                print(f"Error showing message: {error_msg}")

        except Exception as e:
            print(f"Error showing message: {e}")


    def collect_device_info(self):
        """Retrieve and store information for all connected devices."""
        for name, client in self.connections.items():
            self.device_info[name] = {
                "IP": self.devices[next(index for index, d in enumerate(self.devices) if d["name"] == name)]["ip"],
                "Model": self.get_raspi_model(client),
                "RAM": self.get_ram_size(client),
                "MAC_Address": self.get_mac_address(client),
                "net_lag": self.get_lag(client),
                "Temperature": self.get_temperature(client)
                
            }
            msg=f'MI IP: {self.device_info[name]["IP"]} \n MAC: {self.device_info[name]["MAC_Address"]}'
            print(self.show_txt_message_on_screen(client,msg))
        print("Device information collected.")

    def get_all_device_info(self):
        """Retrieve all collected device information."""
        return self.device_info

    def scan_ip_range(self, ip_range):
        """
        Scans the given IP range to detect online devices by pinging each IP address.
        
        Args:
            ip_range (str): IP range in CIDR notation (e.g., '192.168.1.0/24').

        Returns:
            list: A list of online IP addresses.
        """
        online_ips = []
        
        # Detect OS to adjust ping command (Windows/Linux/Mac)
        ping_cmd = ["ping", "-c", "1", "-W", "1"] if platform.system().lower() != "windows" else ["ping", "-n", "1", "-w", "1000"]

        try:
            network = ipaddress.ip_network(ip_range, strict=False)

            for ip in network.hosts():
                ip_str = str(ip)
                command = ping_cmd + [ip_str]

                try:
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode == 0:
                        print(f"Device found at: {ip_str}")
                        online_ips.append(ip_str)
                except Exception as e:
                    print(f"Error pinging {ip_str}: {e}")

        except ValueError:
            print("Invalid IP range format. Please use CIDR notation (e.g., 192.168.1.0/24).")
        
        return online_ips

    def execute_command(self, device_name, command):
        """Execute a custom command on a specific device."""
        if device_name not in self.connections:
            print(f"No active connection for {device_name}")
            return None
        
        client = self.connections[device_name]
        try:
            stdin, stdout, stderr = client.exec_command(command)
            return stdout.read().decode().strip()
        except Exception as e:
            return f"Error: {e}"

    def close_connections(self):
        """Close all SSH connections."""
        for name, conn in self.connections.items():
            conn.close()
            print(f"Closed connection to {name}")
        self.connections.clear()



