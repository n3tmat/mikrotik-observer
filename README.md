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

## Installation

1. Clone the repository:
   git clone https://github.com/n3tmat/mikrotik-observer.git
   cd mikrotik-observer

2. Install dependencies:
   pip install -r requirements.txt

3. Copy the example config and fill in your details:
   cp config.example.ini config.ini
   nano config.ini

4. Run the dashboard:
   python app.py

5. Open your browser and go to:
   http://<raspberry-pi-ip>:5000

## MikroTik Setup

API access must be enabled on your router.
In Winbox: IP → Services → Enable "api" on port 8728.
Create a user with read access or use your admin credentials.

## Project Structure

app.py              — Flask backend, router data collection
templates/index.html — Frontend dashboard
config.ini           — Your local config (not committed)
config.example.ini   — Template for new users
history.db           — SQLite database (auto-created)
mac_vendors.json     — OUI cache (auto-created)