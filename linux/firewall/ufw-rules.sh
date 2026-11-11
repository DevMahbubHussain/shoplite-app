#!/usr/bin/env bash
# Configure Host-Level Firewall (UFW) for ShopLite Nodes
set -euo pipefail

echo "=== Configuring ShopLite Host Firewall (UFW) ==="

# Safety Check: Verify UFW is installed
if ! command -v ufw &>/dev/null; then
    echo "ERROR: ufw command not found. Please install ufw." >&2
    exit 1
fi

# Reset to clean baseline (uncomment in manual execution if desired)
# ufw --force reset

# Baseline Security Policies
echo "Setting default security policies..."
ufw default deny incoming
ufw default allow outgoing

# Inbound Port Rules (Least Privilege)
echo "Allowing essential management and application traffic..."
ufw allow 22/tcp comment 'SSH Remote Administration'
ufw allow 80/tcp comment 'HTTP Ingress Web Traffic'
ufw allow 443/tcp comment 'HTTPS Ingress TLS Web Traffic'

# Enable UFW non-interactively
echo "Enabling UFW..."
ufw --force enable

echo ""
echo "=== UFW Firewall Successfully Configured & Active ==="
ufw status verbose
