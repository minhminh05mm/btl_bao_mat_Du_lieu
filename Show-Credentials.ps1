param([switch]$ShowPassword)
$demoConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime\secrets\config.json') -Raw | ConvertFrom-Json
Write-Host 'Tài khoản: alice, anna, adam, bob, bea, brian, auditor, secadmin'
if ($ShowPassword) { Write-Host ('Mật khẩu lab: '+$demoConfig.lab_password) }
else { Write-Host 'Để hiện mật khẩu sinh riêng cho máy này: .\Show-Credentials.ps1 -ShowPassword' }
Write-Host 'Không đưa thư mục runtime/secrets hoặc runtime/pki vào báo cáo hay kho mã công khai.'
