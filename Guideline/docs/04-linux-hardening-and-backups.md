# 4. Linux Hardening & Backup Automation (Question 3)

This section details how to verify Linux server security configurations, check SSH daemon lockdown, inspect file permissions and ACLs, verify systemd backup timers, and test firewall rules.

---

## 4.1 Users & Groups Setup

Execute or inspect `linux/setup-users-permissions.sh`:

```bash
# Run the hardening setup script (as root or sudo)
sudo bash linux/setup-users-permissions.sh
```

### Verification Commands:
```bash
# Verify ops group existence
getent group ops
# Expected output: ops:x:1001:deploy

# Verify deploy user and group assignment
id deploy
# Expected output: uid=1001(deploy) gid=1001(ops) groups=1001(ops)
```

---

## 4.2 SSH Hardening Verification

Inspect the configuration in `linux/sshd_config` and apply to `/etc/ssh/sshd_config`:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

### Verification Commands:
```bash
# 1. Query the running sshd daemon for active parameters
sshd -T | grep -E "(permitrootlogin|passwordauthentication|pubkeyauthentication)"

# Expected Output:
# permitrootlogin no
# passwordauthentication no
# pubkeyauthentication yes

# 2. Test password authentication rejection (must fail)
ssh -o PreferredAuthentications=password deploy@localhost
# Expected: Permission denied (publickey).
```

---

## 4.3 Directory Permissions & Single POSIX ACL

The audit log directory `/var/log/shoplite/` must be owned by `root:ops` with mode `750` and **exactly one** `setfacl` rule:

```bash
# Check ownership and mode
ls -ld /var/log/shoplite
# Expected: drwxr-x--- 2 root ops ... /var/log/shoplite

# Check ACLs
getfacl /var/log/shoplite
```

### Expected `getfacl` Output:
```text
# file: var/log/shoplite
# owner: root
# group: ops
user::rwx
group::r-x
group:ops:r-x
mask::r-x
other::---
```

::: warning Rubric Note: Why Permission Mode 777 is Prohibited
Permission mode `777` grants universal read, write, and execute permissions to all local accounts and processes. This completely breaks least-privilege principles, allowing arbitrary log tampering, deletion of audit trails, and malicious script injection. Permissions `750` combined with group ACL `g:ops:r-X` safely restricts access to operations staff.
:::

---

## 4.4 Automated Database Backup via systemd

Verify unit files in `linux/systemd/`:
- `shoplite-backup.service` (Type: `oneshot`)
- `shoplite-backup.timer` (`OnCalendar=*-*-* 02:00:00`, `Persistent=true`)

### Verification Commands:
```bash
# 1. Check timer status and next scheduled execution
systemctl status shoplite-backup.timer

# 2. List all active timers
systemctl list-timers --all | grep shoplite-backup
# Expected: Next run scheduled for 02:00:00 UTC

# 3. Trigger manual execution of backup service
sudo systemctl start shoplite-backup.service

# 4. Check backup service execution log
systemctl status shoplite-backup.service
# Expected: code=exited, status=0/SUCCESS

# 5. Verify generated gzipped database backup artifact
ls -lh /var/backups/shoplite/
```

---

## 4.5 Firewall Configuration (UFW)

Review `linux/firewall/ufw-rules.sh`:
- Default: `deny incoming`, `allow outgoing`
- Allowed TCP ports: `22`, `80`, `443`

### Verification Commands:
```bash
# 1. Inspect active UFW status
sudo ufw status verbose

# 2. Check active listening ports
ss -tulpn

# 3. Test port accessibility:
# Port 80 must connect
curl -s -o /dev/null -w "%{http_code}\n" --connect-timeout 3 http://localhost:80

# Port 5432 or 8080 must be dropped/rejected from outside
curl -s --connect-timeout 3 http://localhost:5432 || echo "Port 5432 correctly blocked"
```
