# Multi-Socket and Port Strategy

**Date:** October 16, 2025
**Questions:**
1. Can port 3040 also read?
2. Can several sockets be open at the same time?

---

## Quick Answers

### Q1: Can port 3040 also read?

**Answer: YES ✅** - Port 3040 is specifically for **read-only queries**.

**Port Capabilities:**
- **Port 3040** = Read-only (VGL@, queries) - Can read but **cannot write/control**
- **Port 3041** = Read/Write (VGL@, VLO@, VSW@, all commands) - Full access

### Q2: Can several sockets be open at the same time?

**Answer: LIKELY YES ✅** - Most IP-Enablers support multiple concurrent TCP connections.

**Typical limits:** 4-8 simultaneous connections (depends on Vantage hardware)

---

## Port Comparison

| Feature | Port 3040 (Read-Only) | Port 3041 (Read/Write) |
|---------|----------------------|------------------------|
| **VGL@ (Query loads)** | ✅ Yes | ✅ Yes |
| **VLO@ (Set loads)** | ❌ No | ✅ Yes |
| **VSW@ (Button press)** | ❌ No | ✅ Yes |
| **VOS@ (Monitor buttons)** | ❌ No | ✅ Yes |
| **VOL@ (Monitor loads)** | ❌ No | ✅ Yes |
| **VOD@ (Monitor LEDs)** | ❌ No | ✅ Yes |
| **Use Case** | Status queries only | Full control + monitoring |

---

## Multiple Socket Benefits

### Why Use Multiple Sockets?

**1. Separation of Concerns**
```
Socket 1 (Port 3041) - Event Listener
    ↓
Persistent connection for monitoring
VOS@ / VOL@ / VOD@ events
Never closes

Socket 2 (Port 3041) - Control Commands
    ↓
Short-lived connections for:
VLO@ (set load)
VSW@ (press button)
VGL@ (query load)

Socket 3 (Port 3040 - Optional) - Read-Only Queries
    ↓
For status polling without affecting control socket
VGL@ queries
```

**2. Avoid Command/Event Interference**

**Problem with single socket:**
```
Socket sending VLO@ 101 50\r
    ↓
While waiting for response...
    ↓
Vantage sends LE 1 23 4C 20\r (LED event)
    ↓
❌ Response parsing gets confused!
```

**Solution with multiple sockets:**
```
Event Socket (Port 3041):
    Only receives events (VOS@/VOL@/VOD@)
    Never sends commands
    Clean event stream

Command Socket (Port 3041):
    Sends commands, waits for responses
    No event interference
    Separate connection per request
```

**3. Better Reliability**

- Event listener crash doesn't affect control
- Control commands don't block event stream
- Can restart event listener without disrupting control

**4. Performance**

- Concurrent command execution
- No waiting for event socket to be "free"
- Polling and monitoring can happen simultaneously

---

## Recommended Architecture

### Current Implementation (Single Socket)

```python
# bridge.py currently uses:
event_socket = socket.socket()  # Port 3041, persistent
    ↓
Monitors: VOS@, VOL@, VOD@

qlink_send() = Creates new socket per command  # Port 3041, ephemeral
    ↓
Sends: VLO@, VGL@, VSW@
```

**This is actually GOOD!** ✅

We're already using multiple sockets:
- 1 persistent event socket (monitoring)
- N ephemeral command sockets (created per API call)

---

## Optimal Strategy: What We Already Have! ✅

### Socket 1: Event Listener (Persistent) - Port 3041
```python
# In event_listener_loop()
event_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
event_socket.connect((VANTAGE_IP, 3041))
event_socket.settimeout(None)  # Blocking, persistent

# Enable monitoring
event_socket.send(b"VOS@ 1 1\r")
event_socket.send(b"VOL@ 1\r")
event_socket.send(b"VOD@ 3\r")

# Listen forever
while True:
    data = event_socket.recv(4096)
    # Parse events...
```

**Purpose:**
- Monitors button presses (VOS@)
- Monitors load changes (VOL@)
- Monitors LED changes (VOD@)
- Never sends commands
- Never closes

### Socket 2+: Command Sockets (Ephemeral) - Port 3041
```python
# In qlink_send()
def qlink_send(cmd: str) -> str:
    with socket.create_connection((VANTAGE_IP, 3041), timeout=2.0) as s:
        s.sendall((cmd + "\r").encode("ascii"))
        response = s.recv(1024).decode("ascii")
        return response
    # Socket automatically closes
```

**Purpose:**
- Sends VLO@ (set load)
- Sends VSW@ (press button)
- Sends VGL@ (query load)
- Creates new socket per command
- Closes after response

**Why this works:**
- Event socket never interferes with commands
- Commands never interfere with event stream
- Multiple API calls can execute concurrently
- Clean separation of concerns

---

## When to Use Port 3040 (Read-Only)?

### Use Case: Dedicated Polling Socket

If you want to add initial load polling without using port 3041:

```python
# Optional: Use port 3040 for queries only
def poll_loads_readonly():
    """Poll loads using port 3040 (read-only)"""
    for load_id in loads:
        with socket.create_connection((VANTAGE_IP, 3040), timeout=2.0) as s:
            s.sendall(f"VGL@ {load_id}\r".encode("ascii"))
            level = int(s.recv(1024).decode("ascii").strip())
            load_states[load_id] = level
```

**Benefits:**
- Doesn't interfere with port 3041 control commands
- Dedicated port for status queries
- Can poll aggressively without affecting control performance

**Drawbacks:**
- Slightly more complex (two port numbers to manage)
- Probably unnecessary - port 3041 handles queries fine

**Recommendation:** Only use port 3040 if you're doing **heavy polling** and want to avoid any potential interference with control commands. Otherwise, port 3041 is sufficient.

---

## Connection Limits

### Typical Vantage IP-Enabler Limits

Based on industry standards for embedded TCP/IP devices:

**Estimated limits:** 4-8 concurrent TCP connections

**Our usage:**
1. Event listener socket (persistent)
2. Command sockets (1-3 concurrent during API calls)
3. Total: Usually 2-4 connections active

**Conclusion:** Well within typical limits ✅

### What Happens if Limit Reached?

If Vantage rejects connection:
```python
try:
    socket.create_connection((VANTAGE_IP, 3041))
except ConnectionRefusedError:
    # Vantage at connection limit
    # Wait and retry
```

**Mitigation:**
- Use connection pooling (reuse sockets)
- Limit concurrent API calls
- Current implementation is fine (ephemeral sockets auto-close)

---

## Advanced Multi-Socket Architectures

### Option A: Current (Recommended) ⭐
```
1 Persistent Event Socket (Port 3041)
    + VOS@, VOL@, VOD@ monitoring
    + Runs in background thread

N Ephemeral Command Sockets (Port 3041)
    + VLO@, VSW@, VGL@ commands
    + Created per API call
    + Auto-close after response
```

**Pros:**
- Simple
- Works well
- No interference
- Already implemented ✅

**Cons:**
- None significant

---

### Option B: Dedicated Read Socket (Optional)
```
Socket 1: Event Listener (Port 3041, persistent)
    + VOS@, VOL@, VOD@ monitoring

Socket 2: Read Queries (Port 3040, persistent or pooled)
    + VGL@ queries for polling
    + Dedicated to status queries

Socket 3+: Control Commands (Port 3041, ephemeral)
    + VLO@ (set loads)
    + VSW@ (button press)
```

**Pros:**
- Queries don't compete with control commands
- Can poll more aggressively
- Clear separation of read vs write

**Cons:**
- More complex
- Probably unnecessary
- Need to manage two ports

**Recommendation:** Only if you're doing **heavy continuous polling** (unlikely with monitoring events).

---

### Option C: Connection Pool (Advanced)
```python
from queue import Queue

# Pool of reusable sockets
command_socket_pool = Queue(maxsize=3)

def get_socket():
    try:
        return command_socket_pool.get_nowait()
    except:
        return socket.create_connection((VANTAGE_IP, 3041))

def return_socket(sock):
    try:
        command_socket_pool.put_nowait(sock)
    except:
        sock.close()  # Pool full, discard

def qlink_send(cmd: str) -> str:
    sock = get_socket()
    try:
        sock.sendall((cmd + "\r").encode("ascii"))
        response = sock.recv(1024).decode("ascii")
        return_socket(sock)  # Return to pool
        return response
    except:
        sock.close()
        raise
```

**Pros:**
- Reuses sockets (fewer connections)
- Faster (no connection overhead)
- More efficient for high-volume commands

**Cons:**
- More complex
- Need timeout/keepalive management
- Probably overkill for this application

**Recommendation:** Only if you're sending hundreds of commands per second (unlikely).

---

## Practical Test: Multiple Connections

### Test 1: Can we open multiple sockets to port 3041?

```python
# Test script to run on Pi
import socket
import time

VANTAGE_IP = "YOUR_VANTAGE_IP"

sockets = []

try:
    for i in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((VANTAGE_IP, 3041))
        sockets.append(s)
        print(f"✅ Socket {i+1} connected")
        time.sleep(0.1)

    print(f"\n✅ Successfully opened {len(sockets)} concurrent connections!")

except Exception as e:
    print(f"❌ Failed at socket {len(sockets)+1}: {e}")

finally:
    for s in sockets:
        s.close()
    print(f"Closed all {len(sockets)} sockets")
```

**Expected result:** Should connect 4-8 sockets before failing.

### Test 2: Event socket + command sockets simultaneously

```python
# Event socket (persistent)
event_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
event_sock.connect((VANTAGE_IP, 3041))
event_sock.send(b"VOS@ 1 1\r")

# Command socket 1
cmd_sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cmd_sock1.connect((VANTAGE_IP, 3041))
cmd_sock1.send(b"VGL@ 101\r")
response1 = cmd_sock1.recv(1024)

# Command socket 2
cmd_sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cmd_sock2.connect((VANTAGE_IP, 3041))
cmd_sock2.send(b"VGL@ 102\r")
response2 = cmd_sock2.recv(1024)

# All work simultaneously ✅
```

---

## Recommendations

### ✅ Keep Current Architecture

**What we have (Phase 1):**
1. Persistent event socket on port 3041
2. Ephemeral command sockets on port 3041

**This is OPTIMAL** for our use case:
- Monitoring for automation (VOS@) ✅
- Real-time LED updates (VOD@) ✅
- Real-time load updates (VOL@) ✅
- Control commands (VLO@, VSW@) ✅
- Query commands (VGL@) ✅

### 🟡 Optional Enhancements

**Only add if needed:**

**1. Initial load polling on port 3040**
```python
# If you want to poll loads without using port 3041
async def poll_initial_loads_readonly():
    for load_id in loads:
        with socket.create_connection((VANTAGE_IP, 3040)) as s:
            s.send(f"VGL@ {load_id}\r".encode())
            level = int(s.recv(1024).decode().strip())
```

**Benefit:** Separates polling from control
**Cost:** More complexity
**Verdict:** Probably unnecessary

**2. Connection pooling**
- Only if sending >100 commands/second
- Unlikely for this application
- Current approach is fine

### ❌ Don't Do

**1. Single socket for everything**
```python
# BAD: Don't do this
global_socket = socket.connect((VANTAGE_IP, 3041))
# Use for both events AND commands
# ❌ Events and responses get mixed up
```

**2. Use port 3040 for monitoring**
```python
# BAD: Won't work
socket.connect((VANTAGE_IP, 3040))
socket.send(b"VOS@ 1 1\r")  # ❌ Port 3040 is read-only!
```

---

## Summary

### Port Capabilities

| Port | Read (VGL@) | Write (VLO@) | Monitor (VOS@/VOL@/VOD@) |
|------|------------|--------------|--------------------------|
| 3040 | ✅ Yes | ❌ No | ❌ No |
| 3041 | ✅ Yes | ✅ Yes | ✅ Yes |

### Multiple Sockets

✅ **Supported** - Typical limit: 4-8 concurrent connections

**Current usage:**
- 1 persistent (event monitoring)
- 1-3 ephemeral (commands)
- Total: 2-4 concurrent
- Well within limits ✅

### Architecture Recommendation

**KEEP CURRENT (Phase 1):**
- 1 persistent socket on port 3041 for monitoring
- N ephemeral sockets on port 3041 for commands
- Perfect for automation + LED tracking + control

**OPTIONAL:**
- Add port 3040 for heavy polling (probably unnecessary)
- Add connection pooling (overkill for this app)

---

## Testing Plan

### Test on Real Vantage System

**1. Verify multiple connections work:**
```bash
# On Pi
ssh pi@192.168.1.213
cd qlink-bridge
python3 <<EOF
import socket
s1 = socket.create_connection(("VANTAGE_IP", 3041))
s2 = socket.create_connection(("VANTAGE_IP", 3041))
s3 = socket.create_connection(("VANTAGE_IP", 3041))
print("✅ 3 concurrent connections successful!")
s1.close(); s2.close(); s3.close()
EOF
```

**2. Test port 3040 read-only:**
```bash
python3 <<EOF
import socket
s = socket.create_connection(("VANTAGE_IP", 3040))
s.send(b"VGL@ 101\r")  # ✅ Should work (query)
print(s.recv(1024).decode())
s.send(b"VLO@ 101 50\r")  # ❌ Should fail (write on read-only port)
s.close()
EOF
```

**3. Test monitoring + commands simultaneously:**
```bash
# Check bridge logs while making API calls
journalctl -u qlink-bridge -f

# In another window, make API calls
curl -X POST http://192.168.1.213:8000/load/101/set -d '{"level":50}'
curl http://192.168.1.213:8000/load/101/status

# Should see:
# - Event listener still running ✅
# - Commands executed successfully ✅
# - No interference ✅
```

---

**Conclusion:** Phase 1 architecture is optimal. Multiple sockets work. Port 3040 is available for read-only queries but probably not needed.

**Next:** Test with real Vantage system to confirm connection limits and validate architecture.
