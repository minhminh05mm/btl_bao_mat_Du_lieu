[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$')][string]$RunId,
  [ValidateSet('before','after','draft')][string]$Phase='draft',
  [string]$BeforeManifest,
  [switch]$HostOnly
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$outputDirectory=Join-Path $projectRoot ('results\'+$RunId)
$hostOutput=Join-Path $outputDirectory ('host.'+$Phase+'.json')
if (Test-Path -LiteralPath $hostOutput) { throw 'Refusing to overwrite an existing host manifest.' }
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$issues=New-Object System.Collections.Generic.List[string]

function Read-WslObservation([string[]]$Command) {
  try {
    $value=(& wsl.exe -d bmdl-demo -u root -- @Command 2>$null) -join "`n"
    $code=$LASTEXITCODE
    if ($code -ne 0) { return @{status='unknown';exit_code=$code} }
    return @{status='observed';value=$value.Trim().Replace([string][char]0,'')}
  } catch { return @{status='unknown';reason=$_.Exception.GetType().Name} }
}

$windowsVersion=Get-Item -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$windows=@{
  product_name_registry=$windowsVersion.GetValue('ProductName')
  edition_id=$windowsVersion.GetValue('EditionID')
  display_version=$windowsVersion.GetValue('DisplayVersion')
  build=[string]$windowsVersion.GetValue('CurrentBuild')
  update_build_revision=$windowsVersion.GetValue('UBR')
  platform_version=[System.Environment]::OSVersion.Version.ToString()
  is_64_bit=[System.Environment]::Is64BitOperatingSystem
  note='Registry ProductName can be a legacy label; build and DisplayVersion are retained without inferring a marketing name.'
}
try {
  $observedOs=Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
  $windows.caption=$observedOs.Caption
  $windows.version_cim=$observedOs.Version
  $windows.architecture_cim=$observedOs.OSArchitecture
  $windows.caption_source='Win32_OperatingSystem'
} catch { $issues.Add('Windows marketing caption unavailable; registry/build observations remain explicit.') }
$cpuRegistry=Get-Item -LiteralPath 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0'
$hardware=@{
  cpu_model=([string]$cpuRegistry.GetValue('ProcessorNameString')).Trim()
  logical_processors_available=[System.Environment]::ProcessorCount
  physical_cores=$null
  physical_memory_bytes=$null
  available_memory_bytes=$null
  cpu_model_source='Windows processor registry'
  memory_source='unknown'
}
try {
  $processors=@(Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop)
  $hardware.physical_cores=($processors | Measure-Object -Property NumberOfCores -Sum).Sum
} catch { $issues.Add('Physical CPU cores unavailable through CIM; logical count is observed separately.') }
try {
  if (-not ('BmdlEnvironment.NativeMemory' -as [type])) {
    $tempFolder=Join-Path $projectRoot 'runtime\tmp'
    New-Item -ItemType Directory -Path $tempFolder -Force | Out-Null
    $previousTemp=$env:TEMP; $previousTmp=$env:TMP
    try {
      $env:TEMP=$tempFolder; $env:TMP=$tempFolder
      Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace BmdlEnvironment {
  [StructLayout(LayoutKind.Sequential)] public class MemoryStatus {
    public uint length=(uint)Marshal.SizeOf(typeof(MemoryStatus));
    public uint memoryLoad;
    public ulong totalPhys,availPhys,totalPageFile,availPageFile,totalVirtual,availVirtual,availExtendedVirtual;
  }
  public static class NativeMemory {
    [DllImport("kernel32.dll",SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GlobalMemoryStatusEx([In,Out] MemoryStatus status);
  }
}
'@ | Out-Null
    } finally { $env:TEMP=$previousTemp; $env:TMP=$previousTmp }
  }
  $memory=New-Object BmdlEnvironment.MemoryStatus
  if (-not [BmdlEnvironment.NativeMemory]::GlobalMemoryStatusEx($memory)) { throw 'Memory query failed' }
  $hardware.physical_memory_bytes=$memory.totalPhys
  $hardware.available_memory_bytes=$memory.availPhys
  $hardware.memory_source='Windows GlobalMemoryStatusEx'
} catch { $issues.Add('Physical RAM query unavailable; no capacity inferred.') }

$wslConfigPath=Join-Path $env:USERPROFILE '.wslconfig'
$wslConfig=@{status='not_present';selected_settings=@{};note='Only allowlisted resource/network settings are retained.'}
if (Test-Path -LiteralPath $wslConfigPath) {
  try {
    $section=''; $selected=@{}
    foreach ($line in Get-Content -LiteralPath $wslConfigPath) {
      $trim=$line.Trim()
      if ($trim -match '^\[([^\]]+)\]$') { $section=$Matches[1].ToLower(); continue }
      if ($trim -match '^([A-Za-z]+)\s*=\s*([^#;]*)') {
        $key=$Matches[1].ToLower(); $value=$Matches[2].Trim()
        if ($section -in @('wsl2','experimental') -and $key -in @('memory','processors','swap','localhostforwarding','networkingmode','guiapplications','dnstunneling','firewall','autoproxy','nestedvirtualization','pagereporting','automemoryreclaim')) {
          $selected[$section+'.'+$key]=$value
        }
      }
    }
    $wslConfig=@{status='observed';selected_settings=$selected;sha256=(Get-FileHash -LiteralPath $wslConfigPath -Algorithm SHA256).Hash.ToLower();note='Other settings are excluded; no defaults inferred.'}
  } catch { $wslConfig=@{status='unknown';reason=$_.Exception.GetType().Name} }
}
$osRelease=Read-WslObservation @('cat','/etc/os-release')
$meminfo=Read-WslObservation @('cat','/proc/meminfo')
$wsl=@{distribution='bmdl-demo';kernel=Read-WslObservation @('uname','-r');os_release=@{};
  processors=Read-WslObservation @('getconf','_NPROCESSORS_ONLN');memory=@{};resource_config=$wslConfig;
  docker_compose=Read-WslObservation @('docker','compose','version','--short');
  docker_buildx=Read-WslObservation @('docker','buildx','version')}
if ($osRelease.status -eq 'observed') {
  foreach ($line in ($osRelease.value -split "`n")) {
    if ($line -match '^(ID|NAME|VERSION_ID|PRETTY_NAME)=(.*)$') { $wsl.os_release[$Matches[1]]=$Matches[2].Trim('"') }
  }
} else { $issues.Add('WSL distribution release unavailable.') }
if ($meminfo.status -eq 'observed') {
  foreach ($line in ($meminfo.value -split "`n")) {
    if ($line -match '^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+)\s+kB') { $wsl.memory[$Matches[1]+'_bytes']=[long]$Matches[2]*1024 }
  }
} else { $issues.Add('WSL memory observation unavailable.') }
$manifest=@{
  schema_version=1;captured_at_utc=[DateTime]::UtcNow.ToString('o');run_id=$RunId;phase=$Phase
  windows=$windows;hardware=$hardware;wsl=$wsl;collection_issues=@($issues)
  privacy='No machine serial, user name, environment dump, credentials, proxy URLs or document contents.'
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $hostOutput -Encoding UTF8
if ($HostOnly) { Write-Output ('Host manifest: '+$hostOutput); return }
$linuxRoot='/mnt/'+$projectRoot.Substring(0,1).ToLower()+$projectRoot.Substring(2).Replace('\','/')
$captureArgs=@('exec','bmdl-lab-1','python','-B','/project/scripts/capture_environment.py','--run-id',$RunId,'--phase',$Phase,'--host-manifest',('results/'+$RunId+'/host.'+$Phase+'.json'))
if ($BeforeManifest) {
  $resolvedBefore=[System.IO.Path]::GetFullPath($BeforeManifest)
  $allowedRoot=[System.IO.Path]::GetFullPath((Join-Path $projectRoot 'results'))+[System.IO.Path]::DirectorySeparatorChar
  if (-not $resolvedBefore.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'BeforeManifest must be inside project/results.' }
  $relativeBefore=$resolvedBefore.Substring($projectRoot.Length+1).Replace('\','/')
  $captureArgs+=@('--before-manifest',$relativeBefore)
}
& wsl.exe -d bmdl-demo -u root -- docker @captureArgs
if ($LASTEXITCODE -ne 0) { throw 'Environment capture incomplete; inspect the sanitized validation section.' }
Write-Output ('Environment manifest: '+(Join-Path $outputDirectory ('environment.'+$Phase+'.json')))
