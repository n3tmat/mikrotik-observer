from flask import Flask, jsonify, render_template, Response
import routeros_api
import time
import sqlite3
import csv
import io
from collections import deque
import requests
import json
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)

# --- CONFIGURATION ---
ROUTER_IP = config['router']['ip']
USERNAME = config['router']['username']
PASSWORD = config['router']['password']
WAN_INTERFACE = config['router']['wan_interface']

# --- GLOBAL STATE ---
graph_history = deque(maxlen=60)
traffic_cache = {}
last_db_save = 0  

# --- MAC VENDOR CACHE ---
def load_vendors():
    """Load cached MAC OUIs from JSON."""
    try:
        with open('mac_vendors.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

MAC_VENDORS = load_vendors()

def get_vendor(mac_address):
    """Identify MAC vendor or detect randomized privacy MACs."""
    if not mac_address: return "Unknown"
    
    mac_upper = mac_address.upper()
    
    # 1. Check for randomized MAC (privacy feature)
    if len(mac_upper) >= 2 and mac_upper[1] in ['2', '6', 'A', 'E']:
        return "Randomized MAC (Privacy Feature)"
    
    # Extract 24-bit OUI
    oui = mac_upper[:8]
    
    # 2. Check local cache
    if oui in MAC_VENDORS:
        return MAC_VENDORS[oui]
        
    # 3. Query API if unknown
    try:
        print(f"New MAC detected ({oui})! Querying API...")
        response = requests.get(f"https://api.macvendors.com/{mac_address}", timeout=3)
        
        vendor_name = response.text if response.status_code == 200 else "Generic Device"
            
        # Save to cache
        MAC_VENDORS[oui] = vendor_name
        with open('mac_vendors.json', 'w') as f:
            json.dump(MAC_VENDORS, f, indent=4)
            
        # API rate limit
        time.sleep(1)
        return vendor_name
        
    except Exception as e:
        print(f"API Lookup Failed: {e}")
        return "Generic Device"

# --- DATABASE SETUP ---
def init_db():
    """Initialize SQLite DB for history."""
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS net_stats
                 (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                  connections INTEGER, down_mbps REAL, up_mbps REAL, cpu REAL)''')
    conn.commit()
    conn.close()

init_db()

def get_router_data():
    """Fetch router data, calculate speeds, and log to DB."""
    global traffic_cache, last_db_save
    
    try:
        connection = routeros_api.RouterOsApiPool(ROUTER_IP, username=USERNAME, password=PASSWORD, plaintext_login=True)
        api = connection.get_api()
        current_time = time.time()

        # 1. Total WAN speed
        try:
            traffic = api.get_resource('/interface').call('monitor-traffic', {'interface': WAN_INTERFACE, 'once': 'true'})
            total_down = round(int(traffic[0]['rx-bits-per-second']) / 1000000, 2)
            total_up = round(int(traffic[0]['tx-bits-per-second']) / 1000000, 2)
        except:
            total_down, total_up = 0.0, 0.0

        # 2. System resources
        try:
            res = api.get_resource('/system/resource').get()[0]
            cpu_usage = int(res.get('cpu-load', '0'))
            uptime = res.get('uptime', '00:00:00')
            version = res.get('version', 'Unknown')
            board = res.get('board-name', 'MikroTik')
            
            total_mem = int(res.get('total-memory', 1))
            free_mem = int(res.get('free-memory', 0))
            ram_usage = round(((total_mem - free_mem) / total_mem) * 100, 1)
        except:
            cpu_usage, ram_usage = 0, 0
            uptime, version, board = "N/A", "N/A", "N/A"

        # 3. Active L4 connections
        try:
            conns = api.get_resource('/ip/firewall/connection').get()
            active_connections = len(conns)
        except: active_connections = 0

        # 4. DB logging (every 60s)
        if current_time - last_db_save >= 60:
            try:
                conn = sqlite3.connect('history.db')
                c = conn.cursor()
                c.execute("INSERT INTO net_stats (connections, down_mbps, up_mbps, cpu) VALUES (?, ?, ?, ?)",
                          (active_connections, total_down, total_up, cpu_usage))
                conn.commit()
                conn.close()
                last_db_save = current_time
            except Exception as e: print(f"DB Error: {e}")

        # 5. Device telemetry (DHCP + Queues)
        try:
            leases = api.get_resource('/ip/dhcp-server/lease').get()
            devices_map = {l.get('address'): {'name': l.get('host-name', 'Unknown'), 'mac': l.get('mac-address', '')} for l in leases if l.get('status') == 'bound'}
        except: devices_map = {}

        try:
            queues = api.get_resource('/queue/simple').get()
            queues_dict = {q.get('target', '').split('/')[0]: q for q in queues if q.get('target')}
        except: queues_dict = {}

        final_devices_list = []

        for ip, info in devices_map.items():
            if not ip.startswith('192.168.88.'): continue

            dev_up, dev_down = 0.0, 0.0
            if ip in queues_dict:
                q = queues_dict[ip]
                try:
                    # Calculate speed via byte delta
                    raw_bytes = q.get('bytes', '0/0').split('/')
                    curr_up, curr_down = int(raw_bytes[0]), int(raw_bytes[1])
                    if ip in traffic_cache:
                        prev = traffic_cache[ip]
                        dt = current_time - prev['time']
                        # Prevent division by zero
                        if dt > 0.5:
                            dev_up = round((max(0, curr_up - prev['bytes_up']) * 8) / (1000000 * dt), 2)
                            dev_down = round((max(0, curr_down - prev['bytes_down']) * 8) / (1000000 * dt), 2)
                    traffic_cache[ip] = {'bytes_up': curr_up, 'bytes_down': curr_down, 'time': current_time}
                except: pass

            final_devices_list.append({
                'name': info['name'], 
                'ip': ip, 
                'mac': info['mac'],
                'vendor': get_vendor(info['mac']), 
                'up': dev_up, 
                'down': dev_down
            })

        connection.disconnect()
        
        # Update history and sort
        graph_history.append({'time': time.strftime('%H:%M:%S'), 'down': total_down, 'up': total_up})
        final_devices_list.sort(key=lambda x: x['down'], reverse=True)

        return {
            'status': 'online', 
            'sys': {'cpu': cpu_usage, 'ram': ram_usage, 'uptime': uptime, 'board': board, 'os': version},
            'connections': active_connections,
            'total_down': total_down, 'total_up': total_up,
            'devices': final_devices_list, 'history': list(graph_history)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {'status': 'error'}

# --- ROUTES ---
@app.route('/')
def index():
    """Serve main dashboard."""
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    """Live data endpoint."""
    return jsonify(get_router_data())

@app.route('/api/history_24h')
def history_24h():
    """Fetch last 60 DB records for charts."""
    try:
        conn = sqlite3.connect('history.db')
        c = conn.cursor()
        c.execute("SELECT time(timestamp, 'localtime'), down_mbps, up_mbps, connections FROM net_stats ORDER BY timestamp DESC LIMIT 60")
        data = c.fetchall()
        conn.close()
        
        data.reverse()
        return jsonify({
            'labels': [row[0][:5] for row in data], 
            'download': [row[1] for row in data],
            'upload': [row[2] for row in data],
            'connections': [row[3] for row in data]
        })
    except:
        return jsonify({'labels': [], 'download': [], 'upload': [], 'connections': []})

@app.route('/api/export_csv')
def export_csv():
    """Export DB history as CSV."""
    try:
        conn = sqlite3.connect('history.db')
        c = conn.cursor()
        c.execute("SELECT timestamp, connections, down_mbps, up_mbps, cpu FROM net_stats ORDER BY timestamp DESC")
        data = c.fetchall()
        conn.close()

        # Write to string buffer
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Timestamp', 'Active Connections', 'Download (Mbps)', 'Upload (Mbps)', 'CPU Usage (%)'])
        cw.writerows(data)

        # Return downloadable file
        output = Response(si.getvalue(), mimetype='text/csv')
        output.headers["Content-Disposition"] = "attachment; filename=mikrotik_network_history.csv"
        return output
    except Exception as e:
        return f"Error generating CSV: {e}"

@app.route('/api/clear_db', methods=['POST'])
def clear_db():
    """Clear database and reset history."""
    global graph_history, last_db_save

    try:
        # 1. Wipe the SQLite table
        conn = sqlite3.connect('history.db')
        c = conn.cursor()
        c.execute("DELETE FROM net_stats")
        conn.commit()
        conn.close()

        # 2. Clear the in-memory graph deque
        graph_history.clear()

        # 3. Reset the timer so it immediately logs the next reading
        last_db_save = 0

        return jsonify({"status": "success", "message": "Database wiped, starting fresh."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)