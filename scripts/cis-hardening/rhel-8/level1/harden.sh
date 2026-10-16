#!/bin/bash
# CIS RHEL 8 Benchmark - Level 1 (Server)
# Based on CIS RHEL 8 Benchmark v1.0.0
# This script implements Level 1 (scored) recommendations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/cis-hardening.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting CIS Level 1 hardening for RHEL 8..."

# ============================================================================
# 1. Initial Setup
# ============================================================================

log "1.1 Filesystem Configuration"

# 1.1.1 Ensure mounting of cramfs filesystems is disabled
log "  1.1.1 Disabling cramfs filesystem"
echo "install cramfs /bin/true" >> /etc/modprobe.d/CIS.conf

# 1.1.2 Ensure mounting of squashfs filesystems is disabled
log "  1.1.2 Disabling squashfs filesystem"
echo "install squashfs /bin/true" >> /etc/modprobe.d/CIS.conf

# 1.1.3 Ensure mounting of udf filesystems is disabled
log "  1.1.3 Disabling udf filesystem"
echo "install udf /bin/true" >> /etc/modprobe.d/CIS.conf

# 1.1.21 Ensure sticky bit is set on all world-writable directories
log "  1.1.21 Setting sticky bit on world-writable directories"
df --local -P | awk '{if (NR!=1) print $6}' | xargs -I '{}' find '{}' -xdev -type d \( -perm -0002 -a ! -perm -1000 \) 2>/dev/null | xargs -I '{}' chmod +t '{}'

# 1.1.22 Disable Automounting
log "  1.1.22 Disabling automounting"
systemctl disable autofs 2>/dev/null || true

# ============================================================================
# 1.2 Configure Software Updates
# ============================================================================

log "1.2 Configure Software Updates"

# 1.2.1 Ensure gpgcheck is globally activated
log "  1.2.1 Enabling gpgcheck globally"
if [ -f /etc/dnf/dnf.conf ]; then
    if ! grep -q "^gpgcheck=1" /etc/dnf/dnf.conf; then
        echo "gpgcheck=1" >> /etc/dnf/dnf.conf
    fi
fi

# ============================================================================
# 1.3 Filesystem Integrity Checking
# ============================================================================

log "1.3 Filesystem Integrity Checking"

# 1.3.1 Ensure AIDE is installed
log "  1.3.1 Installing AIDE"
dnf install -y aide 2>/dev/null || yum install -y aide 2>/dev/null || true

# 1.3.2 Ensure filesystem integrity is regularly checked
log "  1.3.2 Configuring AIDE cron job"
if [ -f /usr/sbin/aide ]; then
    /usr/sbin/aide --init
    mv /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz 2>/dev/null || true
    echo "0 5 * * * /usr/sbin/aide --check" | crontab - 2>/dev/null || true
fi

# ============================================================================
# 1.4 Secure Boot Settings
# ============================================================================

log "1.4 Secure Boot Settings"

# 1.4.1 Ensure permissions on bootloader config are configured
log "  1.4.1 Securing bootloader config"
if [ -f /boot/grub2/grub.cfg ]; then
    chmod 600 /boot/grub2/grub.cfg
    chown root:root /boot/grub2/grub.cfg
fi

# 1.4.2 Ensure bootloader password is set
log "  1.4.2 Bootloader password should be set manually (skipped)"

# 1.4.3 Ensure authentication required for single user mode
log "  1.4.3 Configuring single user mode authentication"
if [ -f /usr/lib/systemd/system/rescue.service ]; then
    sed -i 's/ExecStart=.*/ExecStart=-\/bin\/sh -c "\/sbin\/sulogin; \/usr\/bin\/systemctl --job-mode=fail --no-block default"/' /usr/lib/systemd/system/rescue.service
fi

# ============================================================================
# 1.5 Additional Process Hardening
# ============================================================================

log "1.5 Additional Process Hardening"

# 1.5.1 Ensure core dumps are restricted
log "  1.5.1 Restricting core dumps"
echo "* hard core 0" >> /etc/security/limits.conf
echo "fs.suid_dumpable = 0" >> /etc/sysctl.conf
sysctl -w fs.suid_dumpable=0

# 1.5.3 Ensure address space layout randomization (ASLR) is enabled
log "  1.5.3 Enabling ASLR"
echo "kernel.randomize_va_space = 2" >> /etc/sysctl.conf
sysctl -w kernel.randomize_va_space=2

# 1.5.4 Ensure prelink is disabled
log "  1.5.4 Disabling prelink"
dnf remove -y prelink 2>/dev/null || yum remove -y prelink 2>/dev/null || true

# ============================================================================
# 1.6 Mandatory Access Control
# ============================================================================

log "1.6 Mandatory Access Control"

# 1.6.1 Ensure SELinux is installed
log "  1.6.1 Installing SELinux"
dnf install -y libselinux 2>/dev/null || yum install -y libselinux 2>/dev/null || true

# 1.6.2 Ensure SELinux is not disabled in bootloader configuration
log "  1.6.2 Ensuring SELinux is enabled in bootloader"
if [ -f /boot/grub2/grub.cfg ]; then
    if grep -q "selinux=0" /boot/grub2/grub.cfg || grep -q "enforcing=0" /boot/grub2/grub.cfg; then
        log "  WARNING: SELinux is disabled in bootloader. Manual intervention required."
    fi
fi

# 1.6.3 Ensure SELinux policy is configured
log "  1.6.3 Configuring SELinux policy"
if [ -f /etc/selinux/config ]; then
    sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config
    sed -i 's/^SELINUXTYPE=.*/SELINUXTYPE=targeted/' /etc/selinux/config
fi

# 1.6.4 Ensure SETroubleshoot is not installed
log "  1.6.4 Removing SETroubleshoot"
dnf remove -y setroubleshoot 2>/dev/null || yum remove -y setroubleshoot 2>/dev/null || true

# 1.6.5 Ensure the MCS Translation Service (mcstrans) is not installed
log "  1.6.5 Removing mcstrans"
dnf remove -y mcstrans 2>/dev/null || yum remove -y mcstrans 2>/dev/null || true

# ============================================================================
# 1.7 Warning Banners
# ============================================================================

log "1.7 Warning Banners"

# 1.7.1 Ensure message of the day is configured properly
log "  1.7.1 Configuring MOTD"
cat > /etc/motd <<EOF
***************************************************************************
                            NOTICE TO USERS

This computer system is the property of SentinelGrid and is for authorized
use only. Users (authorized or unauthorized) have no explicit or implicit
expectation of privacy.

Any or all uses of this system and all files on this system may be
intercepted, monitored, recorded, copied, audited, inspected, and disclosed
to authorized SentinelGrid personnel, law enforcement personnel, as well as
authorized officials of other agencies, both domestic and foreign.

By using this system, the user consents to such interception, monitoring,
recording, copying, auditing, inspection, and disclosure at the discretion
of authorized SentinelGrid personnel.

Unauthorized or improper use of this system may result in civil and criminal
penalties and administrative or disciplinary action, as appropriate. By
continuing to use this system you indicate your awareness of and consent to
these terms and conditions of use. LOG OFF IMMEDIATELY if you do not agree
to the conditions stated in this warning.
***************************************************************************
EOF

# 1.7.2 Ensure local login warning banner is configured properly
log "  1.7.2 Configuring login banner"
cat > /etc/issue <<EOF
***************************************************************************
                            NOTICE TO USERS

This computer system is the property of SentinelGrid and is for authorized
use only. Users (authorized or unauthorized) have no explicit or implicit
expectation of privacy.

Any or all uses of this system and all files on this system may be
intercepted, monitored, recorded, copied, audited, inspected, and disclosed
to authorized SentinelGrid personnel, law enforcement personnel, as well as
authorized officials of other agencies, both domestic and foreign.

By using this system, the user consents to such interception, monitoring,
recording, copying, auditing, inspection, and disclosure at the discretion
of authorized SentinelGrid personnel.

Unauthorized or improper use of this system may result in civil and criminal
penalties and administrative or disciplinary action, as appropriate. By
continuing to use this system you indicate your awareness of and consent to
these terms and conditions of use. LOG OFF IMMEDIATELY if you do not agree
to the conditions stated in this warning.
***************************************************************************
EOF

# 1.7.3 Ensure remote login warning banner is configured properly
log "  1.7.3 Configuring SSH banner"
cat > /etc/issue.net <<EOF
***************************************************************************
                            NOTICE TO USERS

This computer system is the property of SentinelGrid and is for authorized
use only. Users (authorized or unauthorized) have no explicit or implicit
expectation of privacy.

Any or all uses of this system and all files on this system may be
intercepted, monitored, recorded, copied, audited, inspected, and disclosed
to authorized SentinelGrid personnel, law enforcement personnel, as well as
authorized officials of other agencies, both domestic and foreign.

By using this system, the user consents to such interception, monitoring,
recording, copying, auditing, inspection, and disclosure at the discretion
of authorized SentinelGrid personnel.

Unauthorized or improper use of this system may result in civil and criminal
penalties and administrative or disciplinary action, as appropriate. By
continuing to use this system you indicate your awareness of and consent to
these terms and conditions of use. LOG OFF IMMEDIATELY if you do not agree
to the conditions stated in this warning.
***************************************************************************
EOF

# 1.7.4 Ensure permissions on /etc/motd are configured
log "  1.7.4 Securing MOTD permissions"
chmod 644 /etc/motd
chown root:root /etc/motd

# 1.7.5 Ensure permissions on /etc/issue are configured
log "  1.7.5 Securing issue permissions"
chmod 644 /etc/issue
chown root:root /etc/issue

# 1.7.6 Ensure permissions on /etc/issue.net are configured
log "  1.7.6 Securing issue.net permissions"
chmod 644 /etc/issue.net
chown root:root /etc/issue.net

# ============================================================================
# 1.8 Ensure updates, patches, and additional security software are installed
# ============================================================================

log "1.8 Installing security updates"
dnf update -y --security 2>/dev/null || yum update -y --security 2>/dev/null || yum update -y || true

log "CIS Level 1 hardening complete. Log saved to: $LOG_FILE"
log "NOTE: Some settings require a reboot to take effect."
log "NOTE: SELinux may need to be set to permissive mode temporarily for first boot."

