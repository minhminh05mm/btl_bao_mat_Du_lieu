[CmdletBinding()]
param([switch]$Benchmark)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'scripts\Assert-Space.ps1')
$demoModule = if ($Benchmark) {'lab.benchmark'} else {'lab.runner'}
& wsl.exe -d bmdl-demo -u root -- docker exec bmdl-lab-1 python -m $demoModule
if ($LASTEXITCODE -ne 0) { throw 'Lần chạy kiểm chứng có lỗi. Xem kết quả đã xuất trong results.' }
