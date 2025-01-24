from flask import Flask, jsonify, request, render_template
from pivideo_manager import PiVideoManager
from datetime import datetime

app = Flask(__name__)

# Define a custom filter to format timestamps
@app.template_filter('datetimeformat')
def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    if value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Handle Zulu time
            return dt.strftime(format)
        except ValueError:
            return value  # If parsing fails, return original value
    return "Never"

manager = PiVideoManager("Gofre","192.168.100.0/24")

@app.route('/')
def home():
    """Home page showing device list."""
    devices = manager.get_all_devices()
    setup = manager.get_setup()
    print("setup",setup)
    return render_template('index.html', devices=devices,setup=setup[0])

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """API endpoint to get all devices."""
    devices = manager.get_all_devices()
    return jsonify(devices)

@app.route('/api/add_device', methods=['POST'])
def add_device():
    """API endpoint to add a new device."""
    data = request.json
    name = data.get('name')
    ip = data.get('ip')
    mac = data.get('mac')
    master = data.get('master', False)

    if not name or not ip or not mac:
        return jsonify({"error": "Missing required fields"}), 400

    manager.add_device(name, ip, mac, master)
    return jsonify({"message": "Device added successfully!"})

@app.route('/api/set_master', methods=['POST'])
def set_master():
    """API endpoint to set a master device."""
    data = request.json
    ip = data.get('ip')

    if not ip:
        return jsonify({"error": "Missing IP field"}), 400

    manager.set_master_device(ip)
    return jsonify({"message": f"Master device set to {ip}."})

@app.route('/api/delete_device', methods=['DELETE'])
def delete_device():
    """API endpoint to delete a device."""
    data = request.json
    ip = data.get('ip')

    if not ip:
        return jsonify({"error": "Missing IP field"}), 400

    manager.delete_device(ip)
    return jsonify({"message": f"Device {ip} deleted."})

@app.route('/api/scan', methods=['POST'])
def scan_network():
    """API endpoint to trigger IP scan."""
    ip_range = request.json.get('ip_range', '192.168.100.0/24')
    manager.scan_ip_range(ip_range)
    return jsonify({"message": "Scan completed.", "devices": manager.get_all_devices()})

@app.route('/api/update_device', methods=['POST'])
def update_device():
    """API endpoint to update device fields like name and master status."""
    data = request.get_json()

    ip = data.get('ip')
    name = data.get('name')
    master = data.get('master')

    if not ip or name is None or master is None:
        return jsonify({"error": "Invalid data"}), 400

    manager.update_device_name_and_master(ip, name, master)
    return jsonify({"message": "Device updated successfully."})


@app.route('/api/device_info/<ip>', methods=['GET'])
def get_device_info(ip):
    """API endpoint to fetch detailed information of a specific device."""
    device = manager.get_device_by_ip(ip)
    if device:
        return jsonify(device)
    return jsonify({"error": "Device not found"}), 404

@app.route('/api/device_metrics/<ip>', methods=['GET'])
def get_device_metrics(ip):
    """API endpoint to fetch metrics (temperature, RAM, storage, lag) of a device."""
    client = manager.connect_to_device(ip)
    if client:
        info = manager.get_device_info(client)
        client.close()
        return jsonify(info)
    return jsonify({"error": "Failed to connect to device"}), 400

if __name__ == '__main__':
    app.run(debug=True)
