# CIS Hardening Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains CIS (Center for Internet Security) hardening scripts for various operating systems.

## Supported Operating Systems

1. **Amazon Linux 2** - `amazon-linux-2/`
2. **Ubuntu 22.04 LTS** - `ubuntu-22.04/`
3. **RHEL 8** - `rhel-8/`
4. **Debian 12** - `debian-12/`
5. **Windows Server 2022** - `windows-server-2022/`

## Hardening Levels

Each OS has two levels of hardening:

- **Level 1 (Server)** - Scored recommendations for general-purpose systems
- **Level 2 (Workstation)** - Additional recommendations for high-security environments

## Usage

### Linux Systems

```bash
# Level 1 hardening
sudo ./scripts/cis-hardening/<os>/level1/harden.sh

# Level 2 hardening (after Level 1)
sudo ./scripts/cis-hardening/<os>/level2/harden.sh
```

### Windows Systems

```powershell
# Run as Administrator
.\scripts\cis-hardening\windows-server-2022\level1\harden.ps1
```

## What Gets Hardened

### Level 1 (Server)

- Filesystem configuration
- Software updates configuration
- Filesystem integrity checking (AIDE)
- Secure boot settings
- Process hardening (ASLR, core dumps)
- Mandatory Access Control (SELinux/AppArmor)
- Warning banners
- Security updates installation

### Level 2 (Workstation)

- Additional filesystem restrictions
- Advanced process hardening
- Enhanced logging and auditing
- Network security hardening
- Additional access controls

## Important Notes

1. **Reboot Required**: Some settings require a reboot to take effect
2. **SELinux/AppArmor**: May need to be set to permissive mode temporarily for first boot
3. **Testing**: Always test in a non-production environment first
4. **Backup**: Create a snapshot/backup before running hardening scripts
5. **Logs**: All actions are logged to `/var/log/cis-hardening.log`

## Verification

After hardening, verify compliance:

```bash
# Install CIS benchmark assessment tool (if available)
# Run compliance scan
```

## Customization

Scripts can be customized by:

1. Editing the script directly
2. Setting environment variables (where supported)
3. Creating wrapper scripts that source the main script

## CIS Benchmarks

These scripts are based on:

- CIS Amazon Linux 2 Benchmark v2.0.0
- CIS Ubuntu 22.04 LTS Benchmark v1.0.0
- CIS RHEL 8 Benchmark v1.0.0
- CIS Debian 12 Benchmark v1.0.0
- CIS Windows Server 2022 Benchmark v1.0.0

## Support

For issues or questions, refer to:
- CIS Benchmarks: https://www.cisecurity.org/cis-benchmarks/
- SentinelGrid Documentation: https://docs.sentinelgrid.ai

