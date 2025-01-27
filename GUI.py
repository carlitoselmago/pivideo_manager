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

manager = PiVideoManager()

@app.route('/')
def home():
    """Home page showing device list."""
    
    setups = manager.get_setups()
    for setup in setups:
        print("setup",setup)
        setup["devices"] = manager.get_all_devices_in_iprange(setup["iprange"])
    
    return render_template('index.html', setups=setups)

"""
@app.route('/api/devices', methods=['GET'])
def get_devices():
    #API endpoint to get all devices.
    devices = manager.get_all_devices_in_iprange()
    return jsonify(devices)
"""
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
    ip_range = request.json.get('ip_range')
    
    manager.scan_ip_range(ip_range)
    return jsonify({"message": "Scan completed."})

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


@app.route('/api/device_info/<ip>/<mac>', methods=['GET'])
def get_device_info(ip,mac):
    """API endpoint to fetch detailed information of a specific device."""
    device_info = manager.update_client(ip,mac)
    device = render_template('partials/device.html', device=device_info)
    if device:
        return device
    return jsonify({"error": "Device not found"}), 404

@app.route('/api/show_screen/<ip>/<mac>', methods=['GET'])
def show_screen_info(ip,mac):
    """API endpoint to make a device show info on screeen."""
    device_info = manager.update_client(ip,mac)
    if device_info:
        name="None"
        if device_info["name"]:
            name=device_info["name"]
        manager.show_txt_message_on_screen(ip,name+" "+device_info["ip"])
        return jsonify({"message": "Action sent successfully."})
    return jsonify({"message": "Coult not connect to device."})

@app.route('/api/reboot/<ip>', methods=['GET'])
def reboot_device(ip):
    """API endpoint to make a device reboot."""
  
    manager.reboot_device(ip)
    return jsonify({"message": "Action sent successfully."})

@app.route('/api/playback/<ip>/<action>', methods=['GET'])
def playback_control(ip,action):
    """API endpoint to make a control playback."""
    manager.playback_control(ip,action)
    return jsonify({"message": "Action sent successfully."})

@app.route('/api/playbackall/<iprange>/<action>', methods=['GET'])
def playbackall_control(iprange,action):
    """API endpoint to make a control playback."""
    manager.playbackall_control(iprange.replace("_","/"),action)
    return jsonify({"message": "Action sent successfully."})

@app.route('/api/add_setup', methods=['POST'])
def add_setup():
    data = request.get_json()
    name = data.get('name')
    iprange = data.get('iprange')

    if not name or not iprange:
        return jsonify({'status': 'error', 'message': 'All fields are required'}), 400

    # Store setup (in real-world, save to a database)
    if manager.create_setup(name,iprange):
        return jsonify({'status': 'success', 'message': 'Setup added successfully!', 'setup': {"name":name,"iprange":iprange}})
    else:
        return jsonify({"error": "iprange already exists or bad iprange"})

@app.route('/api/update_device_order', methods=['POST'])
def update_device_order():
    try:
        order_data = request.get_json()
        print("order_data",order_data)

        manager.sort_devices(order_data)
        """
        for item in order_data:
            mac = item['mac']
            order = item['order']
            container_id = item['container_id']

            # Update order in the database (replace with actual DB logic)
            
        """
        return jsonify({'status': 'success', 'message': 'Order updated successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
