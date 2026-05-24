# MikroTik Observer — Network NOC Dashboard

A real-time network monitoring dashboard for MikroTik routers, built on a Raspberry Pi.
Displays live bandwidth, per-device traffic, MAC vendor identification, and historical logging.

## Features

- Live WAN throughput graph (updated every second)
- Per-device bandwidth via MikroTik Simple Queues
- MAC vendor identification with local OUI cache
- MAC randomization detection
- L4 active connection tracking
- SQLite historical logging with CSV export
- Clean dark web UI (Tailwind CSS + Chart.js)

## Requirements

- Raspberry Pi (any model with network access)
- MikroTik router with API access enabled
- Python 3.9+

## MikroTik Router Setup

### 1. Enable API Access
Winbox: IP → Services → enable "api" on port 8728

### 2. Create a monitoring user
System → Users → Add
- Group: read (recommended) or full
- Set username and password — you will use these in config.ini

### 3. DHCP Server
Must be running on the router for device discovery to work.
IP → DHCP Server → verify it is active on your LAN interface

### 4. FastTrack (optional)
By default MikroTik uses FastTrack which bypasses queue counters,
meaning per-device bandwidth will show 0.00 or close to it even with queues configured.

To disable it:
IP → Firewall → Filter Rules → disable the FastTrack rule

Note: This increases CPU usage significantly on low-end routers like the RB951.
Only recommended if your router has enough headroom.

## Installation

### 1. Clone the repository on your Raspberry Pi

```bash
git clone https://github.com/n3tmat/mikrotik-observer.git
cd mikrotik-observer
```

### 2. Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure

```bash
cp config.example.ini config.ini
nano config.ini
```

Fill in your router IP, username, password, and WAN interface name.
To find your WAN interface name, check Winbox: Interfaces → look for the interface connected to your ISP, usually ether1.

### 4. Run

```bash
python3 app.py
```

## Accessing the Dashboard

The dashboard runs on port 5000.

1. Find your Raspberry Pi's IP address:

```bash
hostname -I
```

2. Open a browser on any device on the same network and go to:
http://<raspberry-pi-ip>:5000

For example: `http://192.168.88.10:5000`

Note: Your Pi and the device you are viewing the dashboard on must be connected to the same router.

## Run on Boot (optional)

To start the dashboard automatically when the Pi boots:

```bash
sudo nano /etc/systemd/system/mikrotik-observer.service
```

Paste this:

```ini
[Unit]
Description=MikroTik Observer
After=network.target

[Service]
WorkingDirectory=/home/pi/mikrotik-observer
ExecStart=/usr/bin/python3 /home/pi/mikrotik-observer/app.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl enable mikrotik-observer
sudo systemctl start mikrotik-observer
```

## Project Structure
app.py                 — Flask backend, router data collection
templates/index.html   — Frontend dashboard
config.ini             — Your local config (not committed)
config.example.ini     — Template for new users
history.db             — SQLite database (auto-created)
mac_vendors.json       — OUI cache (auto-created)
