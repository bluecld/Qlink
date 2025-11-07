#!/bin/bash
# Script to set up SSH key authentication to home NAS

NAS_IP="192.168.1.129"
NAS_USER="admin"
SSH_KEY=$(cat ~/.ssh/id_ed25519.pub)

echo "Setting up SSH key authentication for $NAS_USER@$NAS_IP"
echo "You will be prompted for the password"

ssh -o StrictHostKeyChecking=no $NAS_USER@$NAS_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$SSH_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'SSH key added successfully'"

if [ $? -eq 0 ]; then
    echo ""
    echo "Testing passwordless SSH connection..."
    ssh $NAS_USER@$NAS_IP "hostname && echo 'Passwordless SSH working!'"
else
    echo "Failed to set up SSH key"
fi
