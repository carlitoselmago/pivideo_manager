import paramiko
import time
import platform
import ipaddress
import subprocess
import sqlite3
from datetime import datetime
import concurrent.futures
import threading
import unicodedata
import re

class PiVideoManager:

    username = "pi"
    password = "raspberry"
    db_file = "data.db"

    def __init__(self):
        """Initialize the PiVideoManager and setup the database."""
        self.connections = {}
        self.device_info = {}
        
        self.setup_database()

    def setup_database(self):
        """Create the necessary database tables if they do not exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create devices table with additional fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iprange TEXT,
                name TEXT UNIQUE,
                ip TEXT UNIQUE,
                model TEXT,
                mac TEXT UNIQUE,
                temperature TEXT,
                ram TEXT,
                storage TEXT,
                lag TEXT,
                master BOOLEAN DEFAULT FALSE,
                missing BOOLEAN DEFAULT FALSE,
                sort INTEGER DEFAULT 0,
                last_connection TEXT
            )
        ''')

        # Create setup table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS setup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                friendlyurl TEXT,
                iprange TEXT,
                creation_date TEXT,
                last_update TEXT
            )
        ''')

        # Check if admin table exists
        cursor.execute("""
            SELECT count(*) 
            FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        table_exists = cursor.fetchone()[0]

        if not table_exists:
            # Create admin table if it doesn't exist
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT UNIQUE,
                    password TEXT,
                    setup TEXT
                )
            ''')
            
            user = input("Set an admin user: ")
            password = input("Set an admin password: ")

            # Insert admin credentials
            cursor.execute('''
                INSERT INTO users (user, password, setup) VALUES (?, ?,?)
            ''', (user, password,"admin"))
        
        conn.commit()
        conn.close()

    def generate_friendly_url(self,text):
        """
        Converts a given string into a friendly URL format.
        
        Parameters:
            text (str): The input text to be converted.

        Returns:
            str: A friendly URL string.
        """
        # Normalize the text to remove accents and special characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

        # Replace non-alphanumeric characters with hyphens
        text = re.sub(r'[^a-zA-Z0-9]+', '-', text)

        # Remove leading and trailing hyphens
        text = text.strip('-')

        # Convert to lowercase
        text = text.lower()

        return text

    def check_login(self,username,password):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Enables dictionary-like access
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            if user["setup"]:
                return user["setup"]
            else:
                return False
        else:
            return False
        
    def create_setup(self, name, iprange, password):
        print("create_setup password",password)
        # Validate CIDR notation
        try:
            ipaddress.ip_network(iprange, strict=False)  # Allow both network and host IPs
        except ValueError:
            return False  # Invalid CIDR format

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        friendlyname = self.generate_friendly_url(name)

        cursor.execute('SELECT COUNT(*) FROM setup WHERE iprange = ?', (iprange,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO setup (name, iprange, friendlyurl, creation_date, last_update) VALUES (?, ?, ?, ?,?)',
                (name, iprange, friendlyname, datetime.now().isoformat(), datetime.now().isoformat())
            )

            cursor.execute(
                'INSERT INTO users (user, password, setup) VALUES (?, ?, ?)',
                (friendlyname, password,friendlyname)
            )
            conn.commit()
            conn.close()
            return True  # Successfully added to the database

        conn.close()
        return False  # Entry already exists

    def save_device(self, info,iprange=""):
        """Add or update a device in the database based on the MAC address."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        print("gonna save device",iprange,info)
        # Check if the device with the given MAC address exists
        cursor.execute("SELECT COUNT(*) FROM devices WHERE mac = ?", (info.get("mac"),))
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            # If the device exists, update its values
            info["missing"] = False
            update_fields = ', '.join(f"{key} = ?" for key in info if key != "mac")
            values = [info[key] for key in info if key != "mac"]
            values.append(info["mac"])  # Add mac for WHERE clause

            cursor.execute(f"UPDATE devices SET {update_fields} WHERE mac = ?", values)
            print(f"Device with MAC {info['mac']} updated successfully.")
        else:
            info["iprange"]=iprange
            # If the device does not exist, insert it
            columns = ', '.join(info.keys())
            placeholders = ', '.join(['?' for _ in info])
            values = list(info.values())

            cursor.execute(f"INSERT INTO devices ({columns}) VALUES ({placeholders})", values)
            print(f"Device {info.get('name', 'Unknown')} added successfully.")

        conn.commit()
        conn.close()

    def update_device_info(self, ip, info):
        """Update the collected device info in the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE devices SET model = ?, temperature = ?, ram = ?, storage = ?, lag = ?, last_connection = ?
            WHERE ip = ?
        ''', (info["model"], temperature, ram, storage, lag, datetime.now().isoformat(), ip))
        conn.commit()
        conn.close()

    def update_device_name_and_master(self, ip, name, master):
        """Update only the name and master status of the device in the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE devices 
            SET name = ?, master = ? 
            WHERE ip = ?
        ''', (name, master, ip))
        conn.commit()
        conn.close()


    def get_setups(self):
        """Retrieve setup."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT *
            FROM setup
            
        ''')
        setups = cursor.fetchall()
        conn.close()
        
        # Format the device data
        return [
            {
                "id": d[0],
                "name": d[1],
                "friendlyurl": d[2],
                "iprange": d[3],
                "creation_date": d[4],
                "last_update": d[5],
                
            }
            for d in setups
        ]

    def get_setup_by_friendlyurl(self,friendlyurl):
        """Retrieve setup."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM setup WHERE friendlyurl = ?', (friendlyurl,)) 
        d = cursor.fetchone()
        conn.close()
        
        # Format the device data
        return {
                "id": d[0],
                "name": d[1],
                "friendlyurl": d[2],
                "iprange": d[3],
                "creation_date": d[4],
                "last_update": d[5] 
            }
      


    def get_device_by_mac(self,mac):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE mac = ?', (mac,)) 
        device = cursor.fetchone()
        conn.close()
        return dict(device)

    def get_master_ip(self, ip):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query to find a master device with a matching IP
        cursor.execute("SELECT ip FROM devices WHERE master = 1 AND ip LIKE ?", (ip[:ip.rfind('.') + 1] + '%',))
        device = cursor.fetchone()
        conn.close()
        
        return device['ip'] if device else None

 

    def get_all_devices_in_iprange(self,iprange):
        """Retrieve all devices from the database and return as a list of dictionaries."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Enables dictionary-like access
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM devices WHERE iprange = ? ORDER BY sort", (iprange,))
        devices = cursor.fetchall()
        conn.close()
        
        # Convert rows to dictionaries
        return [dict(device) for device in devices]

 
    def get_ping_lag(self, target_ip):
        """Ping the master device to measure lag."""
        try:
            ping_cmd = ["ping", "-c", "1", "-W", "1", target_ip]
            result = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
            if "time=" in output:
                return output.split("time=")[-1].split(" ")[0] + " ms"
            else:
                return "N/A"
        except Exception:
            return "N/A"

    def scan_ip_range(self, ip_range, max_threads=50):
        """Scans the given IP range, updates preexisting devices in the database,
        and identifies missing devices by their MAC addresses."""

        # Retrieve current devices in the given IP range from the database
        db_devices = self.get_all_devices_in_iprange(ip_range)

        # Extract MAC addresses from the database devices
        db_mac_set = {device['mac'] for device in db_devices}  # Set of MAC addresses in the DB

        scanned_macs = set()  # Track discovered MACs during the scan

        def ping_ip(ip):
            """Helper function to ping an IP and return status."""
            ping_cmd = ["ping", "-c", "1", "-W", "1"] if platform.system().lower() != "windows" else ["ping", "-n", "1", "-w", "1000"]
            command = ping_cmd + [ip]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                print(f"Device found at: {ip}")
                client = self.connect_to_device(ip)
                if client:
                    print(f"Client connected at {ip}")
                    
                    # Collect device information including MAC address
                    info = self.collect_device_info(ip, client)
                    #print("info of found device",info)
                    # Add the MAC address to the scanned list
                    if 'mac' in info:
                        scanned_macs.add(info['mac'])
                    
                    self.save_device(info, ip_range)
                    client.close()

        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            ip_list = [str(ip) for ip in network.hosts() if ip.packed[-1] not in {1, 245, 255}]
            print(f"Scanning {len(ip_list)} IPs, using {max_threads} threads...")

            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
                executor.map(ping_ip, ip_list)

            # After scanning, identify missing devices by their MAC addresses
            missing_devices = db_mac_set - scanned_macs

            if missing_devices:
                print(f"Devices missing from the scan (MACs): {missing_devices}")
                self.handle_missing_devices(missing_devices)

        except ValueError:
            print("Invalid IP range format. Please use CIDR notation (e.g., 192.168.1.0/24).")


    def handle_missing_devices(self,devices):
        """It gets a list of mac adresses to flag as missing in the db"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        for mac in devices:
          
            cursor.execute('UPDATE devices SET missing = ? WHERE mac = ?', (True, mac))
        conn.commit()
        conn.close()

    def collect_device_info(self,ip,client):
        """Retrieve and store information for all connected devices."""
        
        info = {
                "ip": ip,
                "model": self.get_raspi_model(client),
                "mac": self.get_mac_address(client),
                "ram": self.get_ram_size(client),
                "lag": self.get_lag(client,ip),
                "storage": self.get_storage(client),
                "temperature": self.get_temperature(client),
                "last_connection":datetime.now().isoformat()
            }
        
        #self.update_device_info(ip,info)
        print("Device information collected.")
        return info
    
    def get_device_by_ip(self, ip):
        client = self.connect_to_device(ip)
        return self.collect_device_info(ip,client)
    
    def update_client(self,ip,mac):
        client = self.connect_to_device(ip)
        if client:
            info = self.collect_device_info(ip,client)
            self.save_device(info)
            #now get the whole data from db
            info_extended = self.get_device_by_mac(mac)
            print("info_extended",info_extended)
            client.close()
        else:
            #client is missing, update and return DB values
            self.handle_missing_devices([mac])
            info_extended = self.get_device_by_mac(mac)
        return info_extended

    def sort_devices(self,devices_order):
        for device in devices_order:
            mac = device["mac"]
            sort = device["order"]
            self.update_device_order(mac,sort)

    def get_mac_address(self, client):
        """Retrieve the MAC address of the Raspberry Pi."""
        try:
            stdin, stdout, stderr = client.exec_command("cat /sys/class/net/eth0/address")
            return stdout.read().decode().strip() or "Unknown MAC"
        except Exception as e:
            return f"Error: {e}"

    def get_temperature(self, client):
        """Retrieve the CPU temperature from the Raspberry Pi."""
        try:
            stdin, stdout, stderr = client.exec_command("vcgencmd measure_temp")
            output = stdout.read().decode().strip()
            return output.split('=')[1] if output else "Unknown"
        except Exception as e:
            return f"Error: {e}"
        
    def get_storage(self, client):
        """Retrieve the used and remaining storage from the Raspberry Pi."""
        try:
            # Execute the `df` command to check disk usage on the root filesystem
            stdin, stdout, stderr = client.exec_command("df -h / | tail -n 1")
            output = stdout.read().decode().strip()

            if output:
                parts = output.split()
                total_storage = parts[1]  # Total size of the filesystem
                used_storage = parts[2]   # Used space
                available_storage = parts[3]  # Available space
                return "T:"+total_storage+" / R:"+available_storage
                """
                return {
                    "total": total_storage,
                    "used": used_storage,
                    "remaining": available_storage
                }
                """
            else:
                return {"error": "No output received"}
        except Exception as e:
            return {"error": str(e)}


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
    
    def get_lag(self, client,ip):
        """Retrieve the lag using ping to the master player."""
        try:
            # Send a single ping request with a 1-second timeout
            stdin, stdout, stderr = client.exec_command(f"ping -c 1 -W 1 {self.get_master_ip(ip)}")
            output = stdout.read().decode().strip()

            # Extract the ping time from the output
            if "time=" in output:
                lag = output.split("time=")[-1].split(" ")[0]
                return f"{round(float(lag),2)} ms"
            else:
                return "Ping failed or no response"
        except Exception as e:
            return f"no master detected {e}"#f"Error: {e}"

    def connect_to_device(self, ip):
        """Establish an SSH connection to a device."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=self.username, password=self.password, timeout=5)
            return client
        except Exception as e:
            print(f"Failed to connect to {ip}: {e}")
            return None

    def update_last_connection(self, mac):
        """Update the last connection time for a device."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET last_connection = ? WHERE mac = ?', (datetime.now().isoformat(), mac))
        conn.commit()
        conn.close()
    
    def update_device_order(self, mac,sort):
        """Update sort for a device."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET sort = ? WHERE mac = ?', (sort, mac))
        conn.commit()
        conn.close()

    def set_master_device(self, ip):
        """Set a specific device as the master."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET master = FALSE')
        cursor.execute('UPDATE devices SET master = TRUE WHERE ip = ?', (ip,))
        conn.commit()
        conn.close()
        print(f"Device {ip} set as master.")

    def show_txt_message_on_screen(self, ip, msg):
        """
        Shows the provided message on the screen of all connected devices using ffmpeg and omxplayer.
        """
        print("Executing show message on",ip,"msg:",msg)
        client = self.connect_to_device(ip)
        self.kill_omxplayer(ip)
        # Construct the ffmpeg command
        escaped_msg = msg.replace(':', r'\:').replace('\n', r'\\ ')

        seconds = 5
        #command = (
        #    f'ffmpeg -y -f lavfi -i "color=c=black:s=1280x720,drawtext=fontfile=/usr/share/fonts/FreeSans.ttf:fontsize=48:text=\'{escaped_msg}\':fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2\" -t 1 -c:v libx264 -pix_fmt yuv420p msg.mp4 && omxplayer msg.mp4 --layer 2 --loop {seconds}'
        #)
        command = (
            f'ffmpeg -y -f lavfi -i color=black:s=320x240 \
        -vf "drawtext=text=\'{escaped_msg}\':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2" \
        -t 5 -r 1 -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p msg.mp4 && omxplayer -b --no-osd msg.mp4 --layer 3'
        )
        print(command)
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
            return True

        except Exception as e:
            print(f"Error showing message: {e}")
        
    def reboot_device(self,ip):
        client = self.connect_to_device(ip)
        command = ('sudo reboot')
        try:
            stdin, stdout, stderr = client.exec_command(command)
            
            # Wait for the command to complete
            while not stdout.channel.exit_status_ready():
                time.sleep(1)

            exit_status = stdout.channel.recv_exit_status()  # Blocks until command is done
            
            if exit_status == 0:
                print("Device reboot message sent.")
            else:
                error_msg = stderr.read().decode()
                print(f"Error trying to reboot: {error_msg}")
            return True
        except Exception as e:
            print(f"Error trying to reboot: {e}")

    def kill_omxplayer(self,ip):
        client = self.connect_to_device(ip)
        command = ('sudo pkill -f omxplayer')
        try:
            stdin, stdout, stderr = client.exec_command(command)
            
            # Wait for the command to complete
            while not stdout.channel.exit_status_ready():
                time.sleep(1)

            exit_status = stdout.channel.recv_exit_status()  # Blocks until command is done
            
            if exit_status == 0:
                print("Device reboot message sent.")
            else:
                error_msg = stderr.read().decode()
                print(f"Error trying to reboot: {error_msg}")
            return True
        except Exception as e:
            print(f"Error trying to reboot: {e}")

    def execute_remote_command(self,ip, command, wait_for_output=True):
        try:
            client = self.connect_to_device(ip)
            
            stdin, stdout, stderr = client.exec_command(command)
            
            if wait_for_output:
                # Wait for the command to complete
                while not stdout.channel.exit_status_ready():
                    time.sleep(1)
                
                exit_status = stdout.channel.recv_exit_status()  # Blocks until command is done
                output = stdout.read().decode()
                error = stderr.read().decode()
                
                if exit_status == 0:
                    print(f"Command executed successfully on {ip}: {output}")
                    return True
                else:
                    print(f"Error executing command on {ip}: {error}")
                    return False
            
            print(f"Command sent to {ip}, not waiting for output.")
            return True
            
        except Exception as e:
            print(f"Error connecting to {ip}: {e}")
            return False
        finally:
            if client:
                client.close()

    ## Playback functions
    def playback_control(self,ip,command="pause"):
        if command=="pause":
            run="sudo -E bash -c 'export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}) && dbus-send --print-reply=literal --session --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Action int32:16 >/dev/null'"
        if command=="mute":
            run = "sudo -E bash -c 'export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}) && dbus-send --print-reply=literal --session --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Set string:\"org.mpris.MediaPlayer2.Player\" string:\"Volume\" variant:double:0.0 >/dev/null'"
        if command=="unmute":
            run = "sudo -E bash -c 'export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/omxplayerdbus.${USER:-root}) && dbus-send --print-reply=literal --session --dest=org.mpris.MediaPlayer2.omxplayer /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Set string:\"org.mpris.MediaPlayer2.Player\" string:\"Volume\" variant:double:1.0 >/dev/null'"
    
        print("playback_control",ip,command)
        self.execute_remote_command(ip,run,wait_for_output=True)
        return True
    
    def playbackall_control(self, iprange, command="pause"):
        # Get devices in iprange
        devices = self.get_all_devices_in_iprange(iprange)
        
        # Define a helper function for threading
        def control_device(ip):
            self.playback_control(ip, command)

        threads = []

        # Create and start a thread for each device
        for d in devices:
            thread = threading.Thread(target=control_device, args=(d["ip"],))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return True


    ## end playback functions

    def close_connections(self):
        """Close all SSH connections."""
        for name, conn in self.connections.items():
            conn.close()
            print(f"Closed connection to {name}")
        self.connections.clear()
