param([double]$MinimumCFreeGB=10,[double]$MinimumEFreeGB=8)
$demoC = Get-PSDrive C
$demoE = Get-PSDrive E
if ($demoC.Free/1GB -lt $MinimumCFreeGB) { throw ('Ổ C chỉ còn '+[math]::Round($demoC.Free/1GB,2)+' GB. Dừng công việc và báo người dùng trước khi tiếp tục.') }
if ($demoE.Free/1GB -lt $MinimumEFreeGB) { throw ('Ổ E chỉ còn '+[math]::Round($demoE.Free/1GB,2)+' GB. Dừng để kiểm tra dung lượng.') }
Write-Host ('Dung lượng trống: C '+[math]::Round($demoC.Free/1GB,2)+' GB; E '+[math]::Round($demoE.Free/1GB,2)+' GB')
