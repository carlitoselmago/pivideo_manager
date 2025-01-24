import paramiko
import time
import platform
import ipaddress
import subprocess
import sqlite3
from datetime import datetime
import concurrent.futures

class PiVideoManager:

    username = "pi"
    password = "raspberry"
    db_file = "devices.db"

    def __init__(self,setupname,iprange):
        """Initialize the PiVideoManager and setup the database."""
        self.connections = {}
        self.device_info = {}
        self.setup_database(setupname,iprange)

    def setup_database(self,setupname,iprange):
        """Create the necessary database tables if they do not exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create devices table with additional fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                ip TEXT UNIQUE,
                model TEXT,
                mac TEXT UNIQUE,
                temperature TEXT,
                ram TEXT,
                storage TEXT,
                lag TEXT,
                master BOOLEAN DEFAULT FALSE,
                sort INTEGER DEFAULT 0,
                last_connection TEXT
            )
        ''')

        # Create setup table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS setup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                iprange TEXT,
                creation_date TEXT,
                last_update TEXT
            )
        ''')

        # Insert default setup if not exists
        cursor.execute('SELECT COUNT(*) FROM setup')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO setup (name, iprange, creation_date, last_update) VALUES (?, ?, ?, ?)',
                           (setupname, iprange, datetime.now().isoformat(), datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def add_device(self, name, ip, model, mac, master=False):
        """Add a new device to the database in the scan process."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO devices (name, ip,  mac, master, last_connection)
            VALUES (?, ?,  ?, ?, ?)
        ''', (name, ip,  mac, master, None))
        conn.commit()
        conn.close()
        print(f"Device {name} added successfully.")

    def update_device_info(self, ip, model, temperature, ram, storage, lag):
        """Update the collected device info in the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE devices SET model = ?, temperature = ?, ram = ?, storage = ?, lag = ?, last_connection = ?
            WHERE ip = ?
        ''', (model, temperature, ram, storage, lag, datetime.now().isoformat(), ip))
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


    def get_setup(self):
        """Retrieve setup."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT *
            FROM setup
            LIMIT 1 
        ''')
        setup = cursor.fetchall()
        conn.close()
        
        # Format the device data
        return [
            {
                "id": d[0],
                "name": d[1],
                "iprange": d[2],
                "creation_date": d[3],
                "last_update": d[4],
                
            }
            for d in setup
        ]

    def get_all_devices(self):
        """Retrieve all devices from the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, ip, mac, temperature, ram, storage, lag, master, sort, last_connection
            FROM devices ORDER BY sort
        ''')
        devices = cursor.fetchall()
        conn.close()
        
        # Format the device data
        return [
            {
                "name": d[0],
                "ip": d[1],
                "mac": d[2],
                "temperature": d[3],
                "ram": d[4],
                "storage": d[5],
                "lag": d[6],
                "master": bool(d[7]),
                "sort": d[8],
                "last_connection": d[9] if d[9] else "Never"
            }
            for d in devices
        ]


    def get_device_info(self, client):
        """Retrieve device details using SSH."""
        try:
            commands = {
                "mac": "cat /sys/class/net/eth0/address",
                "temperature": "vcgencmd measure_temp | cut -d'=' -f2",
                "ram": "free -m | awk '/^Mem:/ {print $2 \" MB\"}'",
                "storage": "df -h / | awk 'NR==2 {print $3 \"/\" $2 \" used\"}'"
            }
            results = {}
            for key, command in commands.items():
                stdin, stdout, stderr = client.exec_command(command)
                results[key] = stdout.read().decode().strip()

            return results
        except Exception as e:
            return {"error": str(e)}

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
        """Scans the given IP range and adds discovered devices to the database, avoiding .1, .245, and .255 IPs."""
        print("ip range",ip_range)
        def ping_ip(ip):
            """Helper function to ping an IP and return status."""
            ping_cmd = ["ping", "-c", "1", "-W", "1"] if platform.system().lower() != "windows" else ["ping", "-n", "1", "-w", "1000"]
            command = ping_cmd + [ip]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print(f"Device found at: {ip}")
                client = self.connect_to_device(ip)
                if client:
                    info = self.get_device_info(client)
                    mac = info.get("mac", "Unknown")
                    self.add_device(f"Device_{mac.replace(':', '_')}", ip, mac)
                    client.close()

        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            ip_list = [str(ip) for ip in network.hosts() if ip.packed[-1] not in {1, 245, 255}]
            print(f"Scanning {len(ip_list)} IPs, using {max_threads} threads...")

            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
                executor.map(ping_ip, ip_list)

        except ValueError:
            print("Invalid IP range format. Please use CIDR notation (e.g., 192.168.1.0/24).")

    def collect_device_info(self,mac):
        """Retrieve and store information for all connected devices."""
        """
          {
                "IP": self.devices[next(index for index, d in enumerate(self.devices) if d["name"] == name)]["ip"],
                "Model": self.get_raspi_model(client),
                "RAM": self.get_ram_size(client),
                "MAC_Address": self.get_mac_address(client),
                "net_lag": self.get_lag(client),
                "Temperature": self.get_temperature(client)
                
            }
        """
          
            
        print("Device information collected.")

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

    def set_master_device(self, ip):
        """Set a specific device as the master."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET master = FALSE')
        cursor.execute('UPDATE devices SET master = TRUE WHERE ip = ?', (ip,))
        conn.commit()
        conn.close()
        print(f"Device {ip} set as master.")

    def close_connections(self):
        """Close all SSH connections."""
        for name, conn in self.connections.items():
            conn.close()
            print(f"Closed connection to {name}")
        self.connections.clear()
