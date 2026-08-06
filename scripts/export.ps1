# Support Bot -- ma'lumotlarni eksport qilish (Windows PowerShell)
#
# Ishlatish:
#   .\scripts\export.ps1
#   .\scripts\export.ps1 -BotApi "http://localhost:8000" -KbApi "http://localhost:8100" -KbKey "YOUR_KEY"
#   .\scripts\export.ps1 -Out "C:\backups\my_backup"

param(
    [string]$BotApi = "http://localhost:8000",
    [string]$KbApi  = "http://localhost:8100",
    [string]$KbKey  = "",
    [string]$Out    = ""
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$folder    = if ($Out) { $Out } else { "backup_$timestamp" }
New-Item -ItemType Directory -Force -Path $folder | Out-Null

Write-Host ""
Write-Host "Backup papkasi: $(Resolve-Path $folder)" -ForegroundColor Cyan
Write-Host ""

# -- 1. Errors -----------------------------------------------------------------
Write-Host "1. Xatoliklar bazasi (errors)..." -ForegroundColor Yellow
try {
    $errors = Invoke-RestMethod -Uri "$BotApi/errors" -Method Get -TimeoutSec 30
    [System.IO.File]::WriteAllText("$folder\errors.json", ($errors | ConvertTo-Json -Depth 10), [System.Text.Encoding]::UTF8)
    Write-Host "   OK -- $($errors.Count) ta yozuv" -ForegroundColor Green
} catch {
    Write-Host "   XATO: $_" -ForegroundColor Red
}

# -- 2. KB entries -------------------------------------------------------------
Write-Host "2. Knowledge Base (kb_entries)..." -ForegroundColor Yellow
if ($KbKey) {
    try {
        $headers    = @{ "X-API-Key" = $KbKey }
        $allEntries = @()
        $offset     = 0
        $limit      = 200
        do {
            $batch = Invoke-RestMethod -Uri "$KbApi/kb/entries" -Method Get `
                     -Headers $headers -TimeoutSec 30 `
                     -Body @{ limit = $limit; offset = $offset }
            $allEntries += $batch
            $offset += $limit
        } while ($batch.Count -eq $limit)
        [System.IO.File]::WriteAllText("$folder\kb_entries.json", ($allEntries | ConvertTo-Json -Depth 10), [System.Text.Encoding]::UTF8)
        Write-Host "   OK -- $($allEntries.Count) ta yozuv" -ForegroundColor Green
    } catch {
        Write-Host "   XATO: $_" -ForegroundColor Red
    }
} else {
    Write-Host "   -KbKey berilmadi -- KB export otkazib yuborildi" -ForegroundColor DarkYellow
}

# -- Meta ----------------------------------------------------------------------
$meta = [ordered]@{
    exported_at = (Get-Date -Format "o")
    bot_api     = $BotApi
    kb_api      = $KbApi
    files       = @(Get-ChildItem $folder | Select-Object -ExpandProperty Name)
}
[System.IO.File]::WriteAllText("$folder\meta.json", ($meta | ConvertTo-Json), [System.Text.Encoding]::UTF8)

Write-Host ""
Write-Host "Eksport tugadi! Papka: $(Resolve-Path $folder)" -ForegroundColor Green
Write-Host ""
