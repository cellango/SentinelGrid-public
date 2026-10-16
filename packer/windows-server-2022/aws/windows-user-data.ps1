# Windows User Data Script for Packer
# This script enables WinRM for Packer communication

<powershell>
# Enable WinRM
winrm quickconfig -q
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

# Configure Windows Firewall
netsh advfirewall firewall add rule name="WinRM-HTTP" dir=in action=allow protocol=TCP localport=5985
netsh advfirewall firewall add rule name="WinRM-HTTPS" dir=in action=allow protocol=TCP localport=5986

# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force
</powershell>

