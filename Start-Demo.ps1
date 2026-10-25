[CmdletBinding()]
param([switch]$Rebuild,[switch]$OpenBrowser)
$ErrorActionPreference='Stop'
$demoRoot = $PSScriptRoot
& (Join-Path $demoRoot 'scripts\Assert-Space.ps1')
function Invoke-DemoLinux {
  & wsl.exe -d bmdl-demo -u root -- @args
  if ($LASTEXITCODE -ne 0) { throw ('Lệnh trong môi trường demo thất bại: '+($args -join ' ')) }
}
$demoDistros = ((& wsl.exe --list --quiet) -join "`n").Replace([string][char]0,'')
if ($demoDistros -notmatch '(?m)^bmdl-demo\s*$') {
  $demoArchive = Join-Path $demoRoot 'downloads\alpine-minirootfs-3.24.2-x86_64.tar.gz'
  New-Item -ItemType Directory -Path (Join-Path $demoRoot 'downloads') -Force | Out-Null
  if (-not (Test-Path -LiteralPath $demoArchive)) { Invoke-WebRequest -Uri 'https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/alpine-minirootfs-3.24.2-x86_64.tar.gz' -OutFile $demoArchive }
  if ((Get-FileHash -LiteralPath $demoArchive -Algorithm SHA256).Hash.ToLower() -ne 'c5ca053cfe1d85c5b96dff8b9bc57045f7f184a30ffb6b65776409ca90388677') { throw 'Rootfs checksum mismatch' }
  New-Item -ItemType Directory -Path (Join-Path $demoRoot 'runtime\wsl') -Force | Out-Null
  & wsl.exe --import bmdl-demo (Join-Path $demoRoot 'runtime\wsl') $demoArchive --version 2
  if ($LASTEXITCODE -ne 0) { throw 'Không tạo được môi trường WSL riêng. Kiểm tra WSL 2 đã được bật.' }
  Invoke-DemoLinux apk add --no-cache docker docker-cli-compose docker-cli-buildx python3 py3-cryptography curl openssl restic
}
$demoLinuxRoot='/mnt/'+$demoRoot.Substring(0,1).ToLower()+$demoRoot.Substring(2).Replace('\','/')
Invoke-DemoLinux sh "$demoLinuxRoot/scripts/start-engine.sh"
Invoke-DemoLinux python3 "$demoLinuxRoot/scripts/prepare.py"
$demoCompose = @('compose','--project-directory',$demoLinuxRoot,'--env-file',"$demoLinuxRoot/.env",'-f',"$demoLinuxRoot/compose.yaml")
if (Test-Path -LiteralPath (Join-Path $demoRoot 'compose.lock.yaml')) { $demoCompose += @('-f',"$demoLinuxRoot/compose.lock.yaml") }
if ($Rebuild) { Invoke-DemoLinux docker @demoCompose build lab }
else {
  & wsl.exe -d bmdl-demo -u root -- docker image inspect bmdl-app:local *> $null
  if ($LASTEXITCODE -ne 0) { Invoke-DemoLinux docker @demoCompose build lab }
}
Invoke-DemoLinux docker @demoCompose up -d postgres keycloak opa openbao
# A new named volume needs ownership for the unprivileged OpenBao service.
$demoImageLock = Get-Content -LiteralPath (Join-Path $demoRoot 'infra\images.lock.json') -Raw | ConvertFrom-Json
$demoBaoImage = $demoImageLock.images.openbao.reference
if ($demoBaoImage -notmatch '@sha256:[a-f0-9]{64}$') { throw 'Thiếu image OpenBao có digest hợp lệ trong images.lock.json.' }
Invoke-DemoLinux docker run --rm --user 0 --entrypoint sh --mount 'source=bmdl_baodata,target=/bao/data' $demoBaoImage -c 'chown -R openbao:openbao /bao/data'
Invoke-DemoLinux docker @demoCompose start openbao
Invoke-DemoLinux docker @demoCompose run --rm --no-deps lab python -m lab.operations init
Invoke-DemoLinux docker exec bmdl-opa-1 /opa check /policies
Invoke-DemoLinux docker @demoCompose up -d api api-baseline gateway lab
Invoke-DemoLinux docker exec bmdl-lab-1 python -m lab.wait_ready
& (Join-Path $demoRoot 'scripts\Assert-Space.ps1')
Write-Host 'Demo sẵn sàng: http://localhost:8088'
if ($OpenBrowser) { Start-Process 'http://localhost:8088' }
