# Raspberry Pi Test Rig Setup Complete

## ✅ Configuration Applied to SD Card (E:\)

### Files Created/Modified:

1. **`E:\ssh`** (empty file)
   - Enables SSH server on first boot
   - Allows remote access via SSH

2. **`E:\userconf.txt`**
   - Username: `pi`
   - Password: `raspberry`
   - Default credentials for initial login

3. **`E:\dhcpcd.conf`**
   - Static IP: `192.168.0.180`
   - Subnet: `255.255.255.0` (/24)
   - Gateway: `192.168.0.1`
   - DNS: `192.168.0.1`, `8.8.8.8`

## 🚀 Next Steps

### 1. Boot the Pi
1. **Remove SD card** from PC (safely eject E:\)
2. **Insert into Raspberry Pi**
3. **Connect Ethernet cable** to your 192.168.0.x network
4. **Power on the Pi** with good 5V power supply
5. **Wait 2-3 minutes** for first boot (it will expand filesystem and configure)

### 2. Verify Network Connection
```powershell
# After Pi boots, test connection
ping 192.168.0.180

# If ping works, try SSH
ssh pi@192.168.0.180
# Password: raspberry
```

### 3. Initial Pi Setup (via SSH)
```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Change default password (recommended!)
passwd

# Install Python 3 and pip (if not already installed)
sudo apt install -y python3 python3-pip python3-venv

# Create directory for bridge
mkdir -p ~/qlink-bridge
```

### 4. Deploy Bridge to Pi

From your Windows PC (after Pi is accessible):

```powershell
# Update deployment config
# Edit config\targets.json:
# Change "host" to "192.168.0.180"
# Change "user" to "pi"
# Change env.VANTAGE_IP to "192.168.0.180" (for testing)

# Deploy
cd C:\Qlink
.\scripts\deploy.ps1
```

### 5. Access Bridge

Once deployed:
- **Web UI**: http://192.168.0.180:8000/ui/
- **Settings**: http://192.168.0.180:8000/ui/settings.html
- **Status**: http://192.168.0.180:8000/monitor/status
- **Health**: http://192.168.0.180:8000/healthz

## 📋 Troubleshooting

### Pi Won't Boot / No Network
- Check **power LED** (red) is solid
- Check **activity LED** (green) blinks during boot
- Verify **Ethernet cable** is good
- Check **Ethernet port LEDs** light up
- Try different power supply (needs 5V 2.5A minimum)

### Can't SSH
```powershell
# Check if Pi is responding
ping 192.168.0.180

# Check if SSH port is open
Test-NetConnection -ComputerName 192.168.0.180 -Port 22

# If timeout, wait longer (first boot takes time)
# If connection refused, SSH might not have started
```

### Can't Connect to Ethernet Port Lights Still Dark
- Try a **different Ethernet cable**
- Try a **different port on switch/router**
- Verify the **Pi Ethernet port** isn't damaged
- Some Pis need extra time - wait 5 minutes

### SSH Works But Can't Deploy
```powershell
# Test SSH connection manually
ssh pi@192.168.0.180
# Enter password: raspberry

# If works, check deploy config
Get-Content config\targets.json

# Verify SSH key path is correct
Test-Path C:\Users\antho\.ssh\id_ed25519
```

## 🔐 Security Notes

**Default Credentials (CHANGE THESE!):**
- Username: `pi`
- Password: `raspberry`

**First thing to do after SSH:**
```bash
passwd  # Change password immediately!
```

**Optional: Add your SSH key**
```bash
# On Pi, create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Copy your public key to authorized_keys
# (Or use ssh-copy-id from Windows)
```

## 🛠️ What's Configured

- ✅ SSH enabled
- ✅ User `pi` created
- ✅ Static IP: 192.168.0.180
- ✅ Gateway: 192.168.0.1
- ✅ Ready for first boot

## 📝 Network Details

```
IP Address: 192.168.0.180
Subnet:     255.255.255.0 (/24)
Gateway:    192.168.0.1
DNS:        192.168.0.1, 8.8.8.8
Hostname:   raspberrypi (default, can change later)
```

## 🎯 Expected Timeline

1. **Insert SD and power on**: 0 min
2. **First boot expansion**: 1-2 min
3. **Service initialization**: 2-3 min
4. **SSH ready**: ~3 min total
5. **Ready to deploy bridge**: ~5 min total

## ✨ After Bridge is Deployed

You'll have:
- REST API for controlling Vantage lights
- Web UI at http://192.168.0.180:8000/ui/
- Settings page for easy configuration
- Real-time event monitoring (when Vantage connected)
- Systemd service (auto-starts on boot)

## 🔄 Next Development Steps

Once Pi is working:
1. Update `config\targets.json` with production Vantage IP (192.168.1.200)
2. Deploy bridge to Pi
3. Test button commands
4. Test event monitoring
5. Extract remaining 355 buttons
6. Full system testing

---

**Ready to boot! Just insert the SD card and power on.** 🚀
