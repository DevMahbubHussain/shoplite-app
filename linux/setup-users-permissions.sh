#!/usr/bin/env bash
# Setup deploy user, ops group, and /var/log/shoplite with correct permissions
set -euo pipefail

echo "=== ShopLite User, Group & Log Directory Setup ==="

# Create ops group and deploy user
groupadd -f ops
id -u deploy &>/dev/null || useradd -m -s /bin/bash -g ops deploy
echo "[OK] User 'deploy' in group 'ops' configured"

# Create and secure log directory
mkdir -p /var/log/shoplite
chown -R root:ops /var/log/shoplite
chmod 750 /var/log/shoplite

# Exactly one POSIX ACL rule — no default-ACL variant
setfacl -R -m g:ops:r-X /var/log/shoplite

echo "[OK] /var/log/shoplite — owner=root:ops, mode=750, ACL=g:ops:r-X"

# Verification output
echo ""
echo "=== Verification ==="
echo "--- User info ---"
id deploy
echo ""
echo "--- Directory listing ---"
ls -ld /var/log/shoplite
echo ""
echo "--- ACL details ---"
getfacl /var/log/shoplite
