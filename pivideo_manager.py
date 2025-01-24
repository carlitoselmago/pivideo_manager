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

    def __init__(self):
        """Initialize the PiVideoManager and setup the database."""
        self.connections = {}
        self.device_info = {}
        self.setup_database()

    def setup_database(self):
        """Create the necessary database tables if they do not exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                ip TEXT UNIQUE,
                master BOOLEAN DEFAULT FALSE,
                sort INTEGER DEFAULT 0,
                last_connection TEXT
            )
        ''')

        # Create setup table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS setup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                creation_date TEXT,
                last_update TEXT
            )
        ''')

        # Insert default setup if not exists
        cursor.execute('SELECT COUNT(*) FROM setup')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO setup (title, creation_date, last_update) VALUES (?, ?, ?)',
                           ('Default Setup', datetime.now().isoformat(), datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def update_setup(self, title):
        """Update the setup title and last update timestamp."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE setup SET title = ?, last_update = ? WHERE id = 1',
                       (title, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_setup_info(self):
        """Retrieve the setup details."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT title, creation_date, last_update FROM setup')
        setup_info = cursor.fetchone()
        conn.close()
        return {"title": setup_info[0], "created": setup_info[1], "updated": setup_info[2]}

    def add_device(self, name, ip, master=False):
        """Add a new device to the database if it is accessible with the default credentials."""
        if self.check_device_access(ip):
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO devices (name, ip, master, last_connection)
                VALUES (?, ?, ?, ?)
            ''', (name, ip, master, None))
            conn.commit()
            conn.close()
            print(f"Device {name} added successfully.")
        else:
            print(f"Device {name} at {ip} is not accessible with the default credentials.")

    def check_device_access(self, ip):
        """Verify if the device can be accessed with default username and password."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=self.username, password=self.password, timeout=5)
            client.close()
            return True
        except Exception:
            return False

    def get_all_devices(self):
        """Retrieve all devices from the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT name, ip, master, sort, last_connection FROM devices ORDER BY sort')
        devices = cursor.fetchall()
        conn.close()
        return [{"name": d[0], "ip": d[1], "master": bool(d[2]), "sort": d[3], "last_connection": d[4]} for d in devices]

    def update_last_connection(self, name):
        """Update the last connection time for a device."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET last_connection = ? WHERE name = ?', (datetime.now().isoformat(), name))
        conn.commit()
        conn.close()

    def connect_to_devices(self):
        """Establish SSH connections to all stored devices."""
        devices = self.get_all_devices()
        for device in devices:
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(hostname=device["ip"], username=self.username, password=self.password, timeout=10)
                self.connections[device["name"]] = client
                self.update_last_connection(device["name"])
                print(f"Connected to {device['name']} ({device['ip']})")
            except Exception as e:
                print(f"Failed to connect to {device['name']} ({device['ip']}): {e}")

    def scan_ip_range(self, ip_range, max_threads=50):
        """Scans the given IP range and adds discovered devices to the database, avoiding .1, .245, and .255 IPs."""

        def ping_ip(ip):
            """Helper function to ping an IP and return status."""
            ping_cmd = ["ping", "-c", "1", "-W", "1"] if platform.system().lower() != "windows" else ["ping", "-n", "1", "-w", "1000"]
            command = ping_cmd + [ip]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                print(f"Device found at: {ip}")
                self.add_device(name=f"Device_{ip.replace('.', '_')}", ip=ip)

        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            ip_list = [str(ip) for ip in network.hosts() if ip.packed[-1] not in {1, 245, 255}]

            print(f"Scanning {len(ip_list)} IPs, using {max_threads} threads...")

            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
                executor.map(ping_ip, ip_list)

        except ValueError:
            print("Invalid IP range format. Please use CIDR notation (e.g., 192.168.1.0/24).")


    def set_master_device(self, ip):
        """Set a specific device as the master."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE devices SET master = FALSE')  # Clear current master
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
