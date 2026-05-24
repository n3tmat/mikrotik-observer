# MikroTik Router Setup

## Required

### 1. Enable API Access
Winbox: IP → Services → enable "api" on port 8728

### 2. Create a user
System → Users → Add
- Group: read (recommended) or full
- Set username and password matching your config.ini

### 3. DHCP Server
Must be running for device discovery to work.
IP → DHCP Server → verify it is active on your LAN interface

## Optional

### 4. Simple Queues (per-device bandwidth)
Devices without a queue will appear in the dashboard but show 0.00 Mbps.
To enable bandwidth tracking for a device:
Queues → Simple Queues → Add
- Target: 192.168.88.x/32 (the device's IP)

### 5. FastTrack (optional)
By default MikroTik uses FastTrack which bypasses queue counters,
meaning per-device bandwidth will show 0.00 even with queues configured.

To fix this, disable the FastTrack firewall rule:
IP → Firewall → Filter Rules → disable the FastTrack rule

Note: This increases CPU usage significantly on low-end routers like the RB951.
Only recommended if your router has enough headroom.
The dashboard will still work without this — per-device bandwidth just won't be accurate.