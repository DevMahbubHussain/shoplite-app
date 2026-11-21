# Phase 2: Linux Hardening (WSL Replication)

## What

The Q3 security baseline — SSH lockdown, dedicated operations accounts, POSIX ACLs on the log directory, UFW firewall, and the nightly backup timer — applied and verified inside a WSL2 Ubuntu 24.04 environment using the repository's `linux/` configuration files.

## Why

The hardening playbook (`ansible/playbooks/harden.yml`) runs against cloud nodes; replicating it locally proves the configuration files themselves are valid and produces verifiable terminal evidence without a cloud VM. WSL2 runs real systemd, so `systemctl`, real `sshd`, and timers behave like a server.

## How

Executed as root inside WSL (WSL permits root shells without a password):

```bash
# Install the toolchain
apt-get update && apt-get install -y openssh-server ufw acl

# Accounts: ops group + deploy user
groupadd -f ops
useradd -m -s /bin/bash -g ops deploy

# SSH lockdown from the repository's hardened config
cp /mnt/e/shoplite-app/linux/sshd_config /etc/ssh/sshd_config
mkdir -p /run/sshd && sshd -t          # validate before restarting
systemctl restart ssh

# Log directory with exactly one POSIX ACL
mkdir -p /var/log/shoplite
chown root:ops /var/log/shoplite
chmod 750 /var/log/shoplite
setfacl -R -m g:ops:r-X /var/log/shoplite

# Backup service + timer from the repository
cp linux/systemd/shoplite-backup.{service,timer} /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now shoplite-backup.timer

# Firewall: default deny, allow only management/web ports
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp; ufw allow 80/tcp; ufw allow 443/tcp
ufw enable
```

## Verification commands (the evidence)

| Checkpoint | Command | Expected |
| :--- | :--- | :--- |
| SSH daemon | `sshd -T \| grep -E "^(permitrootlogin\|passwordauthentication\|pubkeyauthentication)"` | `no` / `no` / `yes` |
| Log directory | `ls -ld /var/log/shoplite && getfacl /var/log/shoplite` | `drwxr-x---+ root ops` + `group:ops:r-x` |
| Backup timer | `systemctl status shoplite-backup.timer` | `active (waiting)` + next schedule |
| Firewall | `ufw status verbose` | `deny (incoming)` + 22/80/443 ALLOW |
| Listening ports | `ss -tulpn` | Only expected services |
| Accounts | `id deploy && getent group ops` | `uid=1001(deploy) gid=1002(ops)` |

## Evidence

<img src="/screenshots/Q3-linux-hardening/B2-log-dir-acl.png" alt="Log ACLs" width="440">
<img src="/screenshots/Q3-linux-hardening/B3-backup-timer.png" alt="Backup timer" width="440">
<img src="/screenshots/Q3-linux-hardening/B4-ufw-firewall.png" alt="UFW firewall" width="440">

<img src="/screenshots/Q3-linux-hardening/B5-open-ports.png" alt="Open ports" width="440">
<img src="/screenshots/Q3-linux-hardening/B6-users-groups.png" alt="Users and groups" width="440">

## Gate

All six checkpoints produce the hardened values; the full command-output record also lives at `linux/evidence/verification-evidence.md`.

Next: [Phase 3 — Terraform Plan](/deploy/03-terraform-plan).
