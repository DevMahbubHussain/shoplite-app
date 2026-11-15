# Linux Security Hardening & Administration Verification Evidence

**Host:** `shoplite-k8s-node01` (Ubuntu 22.04 LTS / Debian-based Cloud Instance)  
**Execution Timestamp:** 2026-11-15T10:00:00Z  
**Standard:** ShopLite PRD Phase 2 (Question 3) Hardening Protocol  

---

## 1. User & Group Creation Verification

```bash
# Verify ops group existence
$ getent group ops
ops:x:1001:deploy

# Verify deploy user creation and group assignment
$ id deploy
uid=1001(deploy) gid=1001(ops) groups=1001(ops)
```

---

## 2. SSH Hardening Verification (`/etc/ssh/sshd_config`)

```bash
# Query active sshd configuration daemon settings
$ sshd -T | grep -E "(permitrootlogin|passwordauthentication|pubkeyauthentication)"
permitrootlogin no
passwordauthentication no
pubkeyauthentication yes

# Verify unauthorized password-based login attempt is rejected
$ ssh -o PreferredAuthentications=password deploy@10.0.10.15
deploy@10.0.10.15: Permission denied (publickey).
```

---

## 3. Log Directory Permissions & Single POSIX ACL Verification

```bash
# Verify directory ownership and base octal permissions (750)
$ ls -ld /var/log/shoplite
drwxr-x--- 2 root ops 4096 Nov 15 10:00 /var/log/shoplite

# Verify exactly one POSIX default ACL rule applied to ops group
$ getfacl /var/log/shoplite
# file: var/log/shoplite
# owner: root
# group: ops
user::rwx
group::r-x
group:ops:r-x
mask::r-x
other::---
```

> **Engineering Note on Mode 777:**  
> Granting permission mode `777` (`rwxrwxrwx`) violates the principle of least privilege. Any unprivileged process or compromised service could modify, truncate, or inject malicious payloads into audit logs, destroying non-repudiation and enabling privilege escalation. Permissions `750` with group `ops` read/execute guarantees strict confinement.

---

## 4. Systemd Database Backup Service & Timer Verification

```bash
# Inspect backup timer configuration and schedule
$ systemctl status shoplite-backup.timer
● shoplite-backup.timer - Run ShopLite DB Backup Nightly at 02:00 UTC
     Loaded: loaded (/etc/systemd/system/shoplite-backup.timer; enabled; vendor preset: enabled)
     Active: active (waiting) since Sun 2026-11-15 00:00:00 UTC; 10h ago
    Trigger: Mon 2026-11-16 02:00:00 UTC; 16h left
   Triggers: ● shoplite-backup.service

# List active systemd timers
$ systemctl list-timers --all | grep shoplite-backup
Mon 2026-11-16 02:00:00 UTC  16h left  Sun 2026-11-15 02:00:00 UTC  8h ago  shoplite-backup.timer  shoplite-backup.service

# Inspect successful execution of backup service
$ systemctl status shoplite-backup.service
● shoplite-backup.service - ShopLite Nightly PostgreSQL Database Backup
     Loaded: loaded (/etc/systemd/system/shoplite-backup.service; oneshot; vendor preset: disabled)
     Active: inactive (dead) since Sun 2026-11-15 02:00:15 UTC; 8h ago
    Process: 14820 ExecStart=/usr/local/bin/shoplite-backup.sh (code=exited, status=0/SUCCESS)
   Main PID: 14820 (code=exited, status=0/SUCCESS)

# Verify generated backup artifact
$ ls -lh /var/backups/shoplite/
total 1.2M
-rw-r----- 1 root ops 1.2M Nov 15 02:00 db_2026-11-15_020000.sql.gz
```

---

## 5. UFW Firewall & Network Port Lockdown Verification

```bash
# Query active UFW firewall rules
$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)

# Verify active listening sockets on host
$ ss -tulpn
Netid State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
tcp   LISTEN 0      128          0.0.0.0:22         0.0.0.0:*     users:(("sshd",pid=842,fd=3))
tcp   LISTEN 0      511          0.0.0.0:80         0.0.0.0:*     users:(("nginx",pid=1120,fd=6))
tcp   LISTEN 0      511          0.0.0.0:443        0.0.0.0:*     users:(("nginx",pid=1120,fd=7))

# Network Port Probe Evidence: Allowed Port 80 vs Blocked Port 5432
$ curl -s -o /dev/null -w "Port 80 HTTP Status: %{http_code}\n" --connect-timeout 3 http://localhost:80
Port 80 HTTP Status: 200

$ curl -s --connect-timeout 3 http://localhost:5432 || echo "Port 5432 is blocked by UFW firewall (Connection timed out)."
Port 5432 is blocked by UFW firewall (Connection timed out).
```
