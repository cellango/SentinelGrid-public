# SentinelGrid OS Image Branding Files

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains branding files for hardened OS images.

## Files

### SSH Banners (Pre-Login)
- `amazon-linux-2-banner.txt`
- `ubuntu-22.04-banner.txt`
- `rhel-8-banner.txt`
- `debian-12-banner.txt`
- `windows-server-2022-banner.txt`

### MOTD (Message of the Day - Post-Login)
- `amazon-linux-2-motd.txt`
- `ubuntu-22.04-motd.txt`
- `rhel-8-motd.txt`
- `debian-12-motd.txt`
- `windows-server-2022-motd.txt`

## Usage

These files are automatically copied during Packer image builds.

### Linux Systems

**SSH Banner:** Copied to `/etc/ssh/sshd_banner` and configured in `sshd_config`  
**MOTD:** Copied to `/etc/motd`  
**System Info:** Generated at `/etc/sentinelgrid-image-info`

### Windows Systems

**Login Message:** Set via registry (legalnoticecaption/legalnoticetext)  
**System Info:** Created at `C:\ProgramData\SentinelGrid\image-info.txt`

## Customization

To customize branding:

1. Edit the appropriate template file
2. Rebuild images with Packer
3. New images will include updated branding

## Branding Guidelines

- Keep banners concise (fits on one screen)
- Include SentinelGrid name and OS type
- Mention CIS hardening level
- Provide documentation links
- Include support contact

## Testing

After building an image:

```bash
# Launch test instance
# SSH to instance
# Verify banner appears before login
# Login and verify MOTD appears
# Check info file exists
cat /etc/sentinelgrid-image-info
```

---

**Created:** December 3, 2025  
**Purpose:** Professional branding for SentinelGrid hardened images

