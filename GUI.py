from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
from pivideo_manager import PiVideoManager
from datetime import datetime
import os

homeurl="/pimanager"

app = Flask(__name__,static_url_path=homeurl+'/static')
app.secret_key = os.environ.get('SECRET_KEY', 'default_fallback_key')



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

# Decorator to require admin login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session:
            # Store the full path (including query string)
            session['next'] = request.full_path
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session['role'] != "admin":
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def roothome():
    return redirect(url_for('home'))

@app.route(homeurl)
@login_required
@admin_required
def home():
    """Home page showing device list."""
    
    setups = manager.get_setups()
    for setup in setups:
        print("setup",setup)
        setup["devices"] = manager.get_all_devices_in_iprange(setup["iprange"])
    
    return render_template('index.html', setups=setups,homeurl=homeurl)



@app.route(homeurl+'/control/<friendlyurl>')
@login_required
def home_lite(friendlyurl):
    # shows a lite control version for few actions over the setup
    setup = manager.get_setup_by_friendlyurl(friendlyurl)
    print(setup)
    return render_template('setuplite.html', setup=setup,homeurl=homeurl)


@app.route(homeurl+'/control/<friendlyurl>/<mac>')
@login_required
def home_lite_device(friendlyurl,mac):
    setup = manager.get_setup_by_friendlyurl(friendlyurl)
    print(setup)
    device = manager.get_device_by_mac(mac)
    print(mac)
    return render_template('setuplitedevice.html', setup=setup,device=device,homeurl=homeurl)

@app.route(homeurl+'/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        userrole = manager.check_login(username, password)
        if userrole:
            session['role'] = userrole
            session["username"] = username
            
            # Handle redirect
            next_url = session.pop('next', None)
            if next_url:
                return redirect(next_url)
            elif userrole == "admin":
                return redirect(url_for('home'))
            else:
                return redirect(url_for('home_lite', friendlyurl=username))
        else:
            return render_template('login.html', error="Invalid username or password")
    return render_template('login.html')

@app.route(homeurl+'/logout')
def logout():
    """Admin logout."""
    session.clear()
    return redirect(url_for('login'))

@app.route(homeurl+'/api/add_device', methods=['POST'])
@login_required
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

@app.route(homeurl+'/api/set_master', methods=['POST'])
@login_required
def set_master():
    """API endpoint to set a master device."""
    data = request.json
    ip = data.get('ip')

    if not ip:
        return jsonify({"error": "Missing IP field"}), 400

    manager.set_master_device(ip)
    return jsonify({"message": f"Master device set to {ip}."})

@app.route(homeurl+'/api/delete_device', methods=['DELETE'])
@login_required
def delete_device():
    """API endpoint to delete a device."""
    data = request.json
    ip = data.get('ip')

    if not ip:
        return jsonify({"error": "Missing IP field"}), 400

    manager.delete_device(ip)
    return jsonify({"message": f"Device {ip} deleted."})

@app.route(homeurl+'/api/scan', methods=['POST'])
@login_required
def scan_network():
    """API endpoint to trigger IP scan."""
    ip_range = request.json.get('ip_range')
    
    manager.scan_ip_range(ip_range)
    return jsonify({"message": "Scan completed."})

@app.route(homeurl+'/api/delete_setup', methods=['POST'])
@login_required
def delete_setup():
    """API endpoint to trigger IP scan."""
    ip_range = request.json.get('ip_range')
    
    manager.delete_setup(ip_range)
    return jsonify({"message": "setup deleted."})

@app.route(homeurl+'/api/update_device', methods=['POST'])
@login_required
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


@app.route(homeurl+'/api/device_info/<ip>/<mac>', methods=['GET'])
@login_required
def get_device_info(ip,mac):
    """API endpoint to fetch detailed information of a specific device."""
    device_info = manager.update_client(ip,mac)
    device = render_template('partials/device.html', device=device_info)
    if device:
        return device
    return jsonify({"error": "Device not found"}), 404

@app.route(homeurl+'/api/show_screen/<ip>/<mac>', methods=['GET'])
@login_required
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

@app.route(homeurl+'/api/reboot/<ip>', methods=['GET'])
@login_required
def reboot_device(ip):
    """API endpoint to make a device reboot."""
  
    manager.reboot_device(ip)
    return jsonify({"message": "Action sent successfully."})

@app.route(homeurl+'/api/playback/<ip>/<action>', methods=['GET'])
@login_required
def playback_control(ip,action):
    """API endpoint to make a control playback."""
    manager.playback_control(ip,action)
    return jsonify({"message": "Action sent successfully."})

@app.route(homeurl+'/api/playbackall/<iprange>/<action>', methods=['GET'])
@login_required
def playbackall_control(iprange,action):
    """API endpoint to make a control playback."""
    manager.playbackall_control(iprange.replace("_","/"),action)
    return jsonify({"message": "Action sent successfully."})

@app.route(homeurl+'/api/add_setup', methods=['POST'])
@login_required
def add_setup():
    data = request.get_json()
    name = data.get('name')
    iprange = data.get('iprange')
    password = data.get('password')

    if not name or not iprange:
        return jsonify({'status': 'error', 'message': 'All fields are required'}), 400

    # Store setup (in real-world, save to a database)
    if manager.create_setup(name,iprange,password):
        return jsonify({'status': 'success', 'message': 'Setup added successfully!', 'setup': {"name":name,"iprange":iprange,"password":password}})
    else:
        return jsonify({"error": "iprange already exists or bad iprange"})

@app.route(homeurl+'/api/update_device_order', methods=['POST'])
@login_required
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
    app.run(host='0.0.0.0', port=5000,debug=True)

