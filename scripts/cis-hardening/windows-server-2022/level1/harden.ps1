# CIS Windows Server 2022 Benchmark - Level 1 (Member Server)
# Based on CIS Windows Server 2022 Benchmark v1.0.0
# This script implements Level 1 (scored) recommendations
# Run as Administrator

$ErrorActionPreference = "Stop"
$LogFile = "C:\Windows\Temp\cis-hardening.log"

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

Write-Log "Starting CIS Level 1 hardening for Windows Server 2022..."

# ============================================================================
# 1. Account Policies
# ============================================================================

Write-Log "1. Account Policies"

# 1.1.1 Ensure 'Enforce password history' is set to '24 or more password(s)'
Write-Log "  1.1.1 Configuring password history"
net accounts /uniquepw:24

# 1.1.2 Ensure 'Maximum password age' is set to '365 or fewer days, but not 0'
Write-Log "  1.1.2 Configuring maximum password age"
net accounts /maxpwage:90

# 1.1.3 Ensure 'Minimum password age' is set to '1 or more day(s)'
Write-Log "  1.1.3 Configuring minimum password age"
net accounts /minpwage:1

# 1.1.4 Ensure 'Minimum password length' is set to '14 or more character(s)'
Write-Log "  1.1.4 Configuring minimum password length"
net accounts /minpwlen:14

# 1.1.5 Ensure 'Password must meet complexity requirements' is set to 'Enabled'
Write-Log "  1.1.5 Enabling password complexity requirements"
secedit /export /cfg C:\Windows\Temp\secpol.cfg
(Get-Content C:\Windows\Temp\secpol.cfg) -replace 'PasswordComplexity = 0', 'PasswordComplexity = 1' | Set-Content C:\Windows\Temp\secpol.cfg
secedit /configure /db C:\Windows\security\local.sdb /cfg C:\Windows\Temp\secpol.cfg /areas SECURITYPOLICY
Remove-Item C:\Windows\Temp\secpol.cfg -Force

# 1.1.6 Ensure 'Store passwords using reversible encryption' is set to 'Disabled'
Write-Log "  1.1.6 Disabling reversible encryption"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "ClearTextPassword" -Value 0

# ============================================================================
# 2. Audit Policy
# ============================================================================

Write-Log "2. Audit Policy"

# 2.2.1 Ensure 'Audit Account Logon' is set to 'Success and Failure'
Write-Log "  2.2.1 Configuring Account Logon auditing"
auditpol /set /subcategory:"Logon" /success:enable /failure:enable

# 2.2.2 Ensure 'Audit Account Management' is set to 'Success and Failure'
Write-Log "  2.2.2 Configuring Account Management auditing"
auditpol /set /subcategory:"User Account Management" /success:enable /failure:enable

# 2.2.3 Ensure 'Audit Directory Service Access' is set to 'Success and Failure' (DC only)
Write-Log "  2.2.3 Configuring Directory Service Access auditing (if DC)"
auditpol /set /subcategory:"Directory Service Access" /success:enable /failure:enable

# 2.2.4 Ensure 'Audit Logon Events' is set to 'Success and Failure'
Write-Log "  2.2.4 Configuring Logon Events auditing"
auditpol /set /subcategory:"Logon" /success:enable /failure:enable

# 2.2.5 Ensure 'Audit Object Access' is set to 'Success and Failure'
Write-Log "  2.2.5 Configuring Object Access auditing"
auditpol /set /subcategory:"File System" /success:enable /failure:enable

# 2.2.6 Ensure 'Audit Policy Change' is set to 'Success and Failure'
Write-Log "  2.2.6 Configuring Policy Change auditing"
auditpol /set /subcategory:"Audit Policy Change" /success:enable /failure:enable

# 2.2.7 Ensure 'Audit Privilege Use' is set to 'Success and Failure'
Write-Log "  2.2.7 Configuring Privilege Use auditing"
auditpol /set /subcategory:"Sensitive Privilege Use" /success:enable /failure:enable

# 2.2.8 Ensure 'Audit Process Tracking' is set to 'Success and Failure'
Write-Log "  2.2.8 Configuring Process Tracking auditing"
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable

# 2.2.9 Ensure 'Audit System Events' is set to 'Success and Failure'
Write-Log "  2.2.9 Configuring System Events auditing"
auditpol /set /subcategory:"System" /success:enable /failure:enable

# ============================================================================
# 3. User Rights Assignment
# ============================================================================

Write-Log "3. User Rights Assignment"

# 3.2.1 Ensure 'Access Credential Manager as a trusted caller' is set to 'No One'
Write-Log "  3.2.1 Removing trusted caller access"
secedit /export /cfg C:\Windows\Temp\secpol.cfg
(Get-Content C:\Windows\Temp\secpol.cfg) -replace 'SeTrustedCredManAccessPrivilege = .*', 'SeTrustedCredManAccessPrivilege =' | Set-Content C:\Windows\Temp\secpol.cfg
secedit /configure /db C:\Windows\security\local.sdb /cfg C:\Windows\Temp\secpol.cfg /areas USER_RIGHTS
Remove-Item C:\Windows\Temp\secpol.cfg -Force

# 3.2.2 Ensure 'Access this computer from the network' is set to 'Administrators, Authenticated Users'
Write-Log "  3.2.2 Configuring network access"
secedit /export /cfg C:\Windows\Temp\secpol.cfg
(Get-Content C:\Windows\Temp\secpol.cfg) -replace 'SeNetworkLogonRight = .*', 'SeNetworkLogonRight = *S-1-5-32-544,*S-1-5-11' | Set-Content C:\Windows\Temp\secpol.cfg
secedit /configure /db C:\Windows\security\local.sdb /cfg C:\Windows\Temp\secpol.cfg /areas USER_RIGHTS
Remove-Item C:\Windows\Temp\secpol.cfg -Force

# 3.2.3 Ensure 'Act as part of the operating system' is set to 'No One'
Write-Log "  3.2.3 Removing operating system access"
secedit /export /cfg C:\Windows\Temp\secpol.cfg
(Get-Content C:\Windows\Temp\secpol.cfg) -replace 'SeTcbPrivilege = .*', 'SeTcbPrivilege =' | Set-Content C:\Windows\Temp\secpol.cfg
secedit /configure /db C:\Windows\security\local.sdb /cfg C:\Windows\Temp\secpol.cfg /areas USER_RIGHTS
Remove-Item C:\Windows\Temp\secpol.cfg -Force

# ============================================================================
# 4. Security Options
# ============================================================================

Write-Log "4. Security Options"

# 4.1.1 Ensure 'Accounts: Administrator account status' is set to 'Disabled'
Write-Log "  4.1.1 Disabling Administrator account (if not needed)"
# net user Administrator /active:no

# 4.1.2 Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'
Write-Log "  4.1.2 Blocking Microsoft accounts"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "NoConnectedUser" -Value 3

# 4.1.3 Ensure 'Accounts: Guest account status' is set to 'Disabled'
Write-Log "  4.1.3 Disabling Guest account"
net user Guest /active:no

# 4.2.1 Ensure 'Audit: Force audit policy subcategory settings' is set to 'Enabled'
Write-Log "  4.2.1 Enabling audit policy subcategory settings"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "SCENoApplyLegacyAuditPolicy" -Value 1

# 4.3.1 Ensure 'Devices: Allowed to format and eject removable media' is set to 'Administrators'
Write-Log "  4.3.1 Restricting removable media formatting"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name "AllocateDASD" -Value "0"

# 4.4.1 Ensure 'Domain member: Digitally encrypt or sign secure channel data (always)' is set to 'Enabled'
Write-Log "  4.4.1 Enabling secure channel encryption"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Netlogon\Parameters" -Name "RequireStrongKey" -Value 1

# 4.5.1 Ensure 'Interactive logon: Do not display last user name' is set to 'Enabled'
Write-Log "  4.5.1 Hiding last user name"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "DontDisplayLastUserName" -Value 1

# 4.5.2 Ensure 'Interactive logon: Require Domain Controller authentication to unlock workstation' is set to 'Enabled'
Write-Log "  4.5.2 Requiring DC authentication for unlock"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" -Name "ForceUnlockLogon" -Value 1

# 4.6.1 Ensure 'Microsoft network client: Digitally sign communications (always)' is set to 'Enabled'
Write-Log "  4.6.1 Enabling SMB signing"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" -Name "RequireSecuritySignature" -Value 1

# 4.6.2 Ensure 'Microsoft network server: Digitally sign communications (always)' is set to 'Enabled'
Write-Log "  4.6.2 Enabling SMB server signing"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "RequireSecuritySignature" -Value 1

# 4.7.1 Ensure 'Network access: Allow anonymous SID/Name translation' is set to 'Disabled'
Write-Log "  4.7.1 Disabling anonymous SID translation"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "RestrictAnonymousSAM" -Value 1

# 4.7.2 Ensure 'Network access: Do not allow anonymous enumeration of SAM accounts' is set to 'Enabled'
Write-Log "  4.7.2 Preventing anonymous SAM enumeration"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "RestrictAnonymous" -Value 1

# 4.7.3 Ensure 'Network access: Do not allow anonymous enumeration of SAM accounts and shares' is set to 'Enabled'
Write-Log "  4.7.3 Preventing anonymous SAM and share enumeration"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "RestrictAnonymous" -Value 1

# 4.8.1 Ensure 'Network security: Allow Local System to use computer identity for NTLM' is set to 'Enabled'
Write-Log "  4.8.1 Allowing Local System NTLM identity"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa" -Name "UseMachineId" -Value 1

# 4.8.2 Ensure 'Network security: Restrict NTLM: Audit NTLM authentication in this domain' is set to 'Enable all'
Write-Log "  4.8.2 Auditing NTLM authentication"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Lsa\MSV1_0" -Name "RestrictSendingNTLMTraffic" -Value 2

# 4.9.1 Ensure 'Recovery console: Allow automatic administrative logon' is set to 'Disabled'
Write-Log "  4.9.1 Disabling automatic admin logon"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Setup\RecoveryConsole" -Name "SecurityLevel" -Value 0

# 4.10.1 Ensure 'Shutdown: Allow system to be shut down without having to log on' is set to 'Disabled'
Write-Log "  4.10.1 Requiring logon for shutdown"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ShutdownWithoutLogon" -Value 0

# 4.11.1 Ensure 'System: Consent Prompt Behavior Admin' is set to 'Prompt for consent for non-Windows binaries'
Write-Log "  4.11.1 Configuring UAC consent prompt"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorAdmin" -Value 1

# 4.11.2 Ensure 'System: Consent Prompt Behavior User' is set to 'Automatically deny elevation requests'
Write-Log "  4.11.2 Configuring user UAC prompt"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorUser" -Value 0

# 4.11.3 Ensure 'System: Detect application installations and prompt for elevation' is set to 'Enabled'
Write-Log "  4.11.3 Enabling application installation detection"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableInstallerDetection" -Value 1

# 4.11.4 Ensure 'System: Only elevate UIAccess applications that are installed in secure locations' is set to 'Enabled'
Write-Log "  4.11.4 Restricting UIAccess elevation"
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableSecureUIAPaths" -Value 1

# ============================================================================
# 5. Event Log
# ============================================================================

Write-Log "5. Event Log"

# 5.1.1 Ensure 'Application: Specify the maximum log file size (KB)' is set to 'Enabled: 32,768 or greater'
Write-Log "  5.1.1 Configuring Application log size"
wevtutil sl Application /ms:32768

# 5.1.2 Ensure 'Security: Specify the maximum log file size (KB)' is set to 'Enabled: 196,608 or greater'
Write-Log "  5.1.2 Configuring Security log size"
wevtutil sl Security /ms:196608

# 5.1.3 Ensure 'System: Specify the maximum log file size (KB)' is set to 'Enabled: 32,768 or greater'
Write-Log "  5.1.3 Configuring System log size"
wevtutil sl System /ms:32768

# ============================================================================
# 6. Additional Security Settings
# ============================================================================

Write-Log "6. Additional Security Settings"

# Enable Windows Firewall
Write-Log "  Enabling Windows Firewall"
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# Enable Windows Update
Write-Log "  Configuring Windows Update"
Set-Service -Name wuauserv -StartupType Automatic
Start-Service -Name wuauserv

Write-Log "CIS Level 1 hardening complete. Log saved to: $LogFile"
Write-Log "NOTE: Some settings may require a reboot to take effect."
Write-Log "NOTE: Review and test all settings before deploying to production."

