$ErrorActionPreference='Stop'
$demoRoot=$PSScriptRoot
$demoLinuxRoot='/mnt/'+$demoRoot.Substring(0,1).ToLower()+$demoRoot.Substring(2).Replace('\','/')
& wsl.exe -d bmdl-demo -u root -- docker compose --project-directory "$demoLinuxRoot" --env-file "$demoLinuxRoot/.env" -f "$demoLinuxRoot/compose.yaml" stop
if ($LASTEXITCODE -ne 0) { throw 'Không dừng được dịch vụ demo.' }
& wsl.exe --terminate bmdl-demo
if ($LASTEXITCODE -ne 0) { throw 'Không dừng được môi trường WSL riêng.' }
Write-Host 'Đã dừng môi trường demo riêng. Dữ liệu, snapshot và kết quả vẫn được giữ trên E.'
