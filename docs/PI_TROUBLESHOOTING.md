# Raspberry Pi Model B v1.2 Troubleshooting

## Problem: No Network Lights After Boot

### Quick Checklist:

1. **Power Supply**
   - Pi Model B v1.2 needs 5V, 1.2A minimum (recommend 2A)
   - Red LED on? → Power is good
   - No red LED? → Bad power supply or cable
   - Green LED activity? → SD card is being read

2. **Ethernet Cable**
   - Try a different Ethernet cable
   - Confirm cable works (test on another device)
   - Plug directly into router/switch (not through hub)

3. **First Boot Timing**
   - First boot takes 2-5 minutes (Pi is resizing filesystem)
   - You may NOT see network lights immediately
   - Wait 5 full minutes before troubleshooting

4. **Network Port on Pi**
   - Pi Model B v1.2 has onboard 10/100 Ethernet (right side)
   - Port should have 2 small LEDs (green/orange) when connected
   - LEDs appear when network link is established

### Diagnostic Steps:

#### Step 1: Check Power LED
- **Red LED solid**: Good power
- **Red LED flickering/off**: Bad power supply - try different one
- **Green LED flashing**: SD card activity (good sign!)

#### Step 2: Wait 5 Minutes
The Pi is likely:
- Resizing the filesystem on first boot
- Generating SSH keys
- Starting services

Network may not come up until this completes.

#### Step 3: Check Router
- Log into your router's admin panel
- Look for new device "pi-test-rig" in DHCP clients
- If it appears, note the IP address

#### Step 4: Try Direct Connection
If router doesn't show the Pi:
```powershell
# On Windows laptop, share internet connection:
# 1. Unplug Pi from router
# 2. Connect Pi directly to laptop Ethernet port
# 3. Windows will auto-assign 169.254.x.x address
# 4. Wait 2 minutes, then scan:
arp -a | Select-String "169.254"
```

#### Step 5: SD Card Re-Flash
If nothing works after 10 minutes:
1. Power off Pi
2. Remove SD card
3. Re-flash with Raspberry Pi Imager
4. **Important**: Click Settings (⚙) before writing:
   - ✅ Enable SSH
   - ✅ Set username/password
   - ✅ Set hostname
5. Write again and retry

### Common Issues:

#### Issue: Network Port Physically Damaged
- The RJ45 port clips may be broken
- Cable doesn't "click" into place
- **Solution**: Carefully insert cable, ensure it locks

#### Issue: Incompatible Ethernet Switch
- Some managed switches don't auto-negotiate 10/100
- **Solution**: Try plugging directly into router

#### Issue: SD Card Not Fully Imaged
- If you ejected too early, image may be incomplete
- **Solution**: Re-flash and wait for "Success!" message

#### Issue: Power Supply Too Weak
- Pi Model B v1.2 draws ~700mA (more under load)
- Cheap USB chargers may not deliver enough
- **Solution**: Use 2A+ power supply

### Alternative: USB-to-Serial Console

If network never works, you can access the Pi via serial console:
1. Get USB-to-TTL serial cable (3.3V!)
2. Connect to GPIO pins 8 (TX), 10 (RX), 6 (GND)
3. Use PuTTY or screen at 115200 baud
4. This gives you direct console access

### Expected Boot Sequence:

1. **0-10 sec**: Red LED on, green LED flashes (reading SD)
2. **10-60 sec**: Green LED active (kernel loading)
3. **60-120 sec**: Network lights appear (if working)
4. **120-300 sec**: First boot filesystem resize completes
5. **After 300 sec**: SSH should be available

### Test Commands After You Get In:

```bash
# Check network interface
ip addr show eth0

# Check if SSH is running
sudo systemctl status ssh

# Check system resources
free -h
df -h

# Test internet connectivity
ping -c 3 8.8.8.8
```

### Next Steps:

1. **Right now**: Wait 10 full minutes with power on
2. **Then check**: Router DHCP table for pi-test-rig
3. **If still nothing**: Re-flash SD card
4. **If re-flash fails**: Try different SD card (could be faulty)
