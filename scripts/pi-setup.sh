#!/bin/bash
# Raspberry Pi Test Rig Setup Script
# Run this on the Pi after SSH'ing in

set -e  # Exit on error

echo "=========================================="
echo "Qlink Bridge Test Rig Setup"
echo "Raspberry Pi Model B v1.2"
echo "=========================================="
echo ""

# Check system info
echo "📊 System Information:"
echo "  Hostname: $(hostname)"
echo "  IP Address: $(hostname -I)"
echo "  OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "  Kernel: $(uname -r)"
echo "  Architecture: $(uname -m)"
echo "  Memory: $(free -h | grep Mem | awk '{print $2}')"
echo ""

# Update system
echo "🔄 Updating system packages (this may take a while on Pi B v1.2)..."
sudo apt-get update -qq
echo "✅ Package lists updated"
echo ""

# Install Python 3 and pip
echo "🐍 Installing Python 3 and dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git
echo "  Python version: $(python3 --version)"
echo "  Pip version: $(pip3 --version)"
echo "✅ Python installed"
echo ""

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/qlink-bridge
cd ~/qlink-bridge
echo "  Working directory: $(pwd)"
echo "✅ Directory created"
echo ""

# Create virtual environment
echo "🔨 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
echo "✅ Virtual environment ready"
echo ""

# Install Python dependencies
echo "📦 Installing Python packages (FastAPI, uvicorn, etc.)..."
pip install fastapi uvicorn pydantic
echo "✅ Packages installed"
echo ""

echo "=========================================="
echo "✅ Base setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy bridge files from Windows to Pi"
echo "2. Test with mock Vantage server"
echo "3. Configure for real Vantage system"
echo ""
echo "To copy files from Windows, run on your laptop:"
echo "  scp -r c:\\Qlink\\app pi@192.168.0.180:~/qlink-bridge/"
echo "  scp -r c:\\Qlink\\scripts pi@192.168.0.180:~/qlink-bridge/"
echo ""
echo "Virtual environment is activated. To activate later:"
echo "  cd ~/qlink-bridge && source venv/bin/activate"
echo ""
