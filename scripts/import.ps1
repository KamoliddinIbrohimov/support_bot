# Support Bot -- ma'lumotlarni import qilish (Windows PowerShell)
#
# Ishlatish:
#   .\scripts\import.ps1 -From ".\backup_20260805_120000"
#   .\scripts\import.ps1 -From ".\backup_20260805_120000" -BotApi "http://NEW-SERVER:8000"
#   .\scripts\import.ps1 -From ".\backup_20260805_120000" -KbApi "http://NEW-SERVER:8100" -KbKey "NEW_KEY"
#   .\scripts\import.ps1 -From ".\backup_20260805_120000" -DryRun

param(
    [Parameter(Mandatory=$true)]
    [string]$From,
    [string]$BotApi = "http://localhost:8000",
    [string]$KbApi  = "http://localhost:8100",
    [string]$KbKey  = "",
    [string]$Only   = "",
    [switch]$DryRun
)

$isDryRun = $DryRun.IsPresent
$dryLabel = if ($isDryRun) { " [DRY-RUN]" } else { "" }

if (-not (Test-Path $From)) {
    Write-Host "XATO: Papka topilmadi: $From" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ("Import" + $dryLabel + ": " + (Resolve-Path $From)) -ForegroundColor Cyan

$metaFile = Join-Path $From "meta.json"
if (Test-Path $metaFile) {
    $meta = [System.IO.File]::ReadAllText($metaFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    Write-Host "  Eksport sanasi: $($meta.exported_at)"
    Write-Host "  Manba Bot API:  $($meta.bot_api)"
}
Write-Host ""

# ── 1. Errors ------------------------------------------------------------------
if ($Only -eq "" -or $Only -eq "errors") {
    Write-Host "1. Xatoliklar (errors)..." -ForegroundColor Yellow
    $errFile = Join-Path $From "errors.json"
    if (-not (Test-Path $errFile)) {
        Write-Host "   errors.json topilmadi" -ForegroundColor DarkYellow
    } else {
        $errors = [System.IO.File]::ReadAllText($errFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        Write-Host "   $($errors.Count) ta yozuv o'qildi"
        $ok = 0; $skip = 0; $fail = 0
        foreach ($e in $errors) {
            if ($isDryRun) {
                Write-Host "   [dry-run] POST errors -- $($e.title)"
                $ok++
                continue
            }
            # null fieldlarni chiqarib tashlab payload yaratamiz
            $payload = [ordered]@{ title = $e.title; keywords = $e.keywords; solution = $e.solution }
            if ($e.description)   { $payload["description"]   = $e.description }
            if ($e.title_ru)      { $payload["title_ru"]      = $e.title_ru }
            if ($e.title_uz)      { $payload["title_uz"]      = $e.title_uz }
            if ($e.solution_ru)   { $payload["solution_ru"]   = $e.solution_ru }
            if ($e.solution_uz)   { $payload["solution_uz"]   = $e.solution_uz }
            if ($e.keywords_ru)   { $payload["keywords_ru"]   = $e.keywords_ru }
            if ($e.keywords_uz)   { $payload["keywords_uz"]   = $e.keywords_uz }

            try {
                $body = $payload | ConvertTo-Json -Depth 5 -Compress
                $r = Invoke-WebRequest -Uri "$BotApi/errors" -Method Post `
                     -ContentType "application/json; charset=utf-8" `
                     -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
                     -TimeoutSec 15 -ErrorAction Stop
                if ($r.StatusCode -eq 201) { $ok++ }
                else { $skip++ }
            } catch {
                $code = $_.Exception.Response.StatusCode.value__
                if ($code -eq 409) { $skip++ }
                else {
                    Write-Host "   XATO ($($e.title)): $code -- $($_.Exception.Message)" -ForegroundColor Red
                    $fail++
                }
            }
        }
        Write-Host "   OK: $ok import, $skip mavjud, $fail xatolik" -ForegroundColor Green
    }
}

# ── 2. KB entries --------------------------------------------------------------
if ($Only -eq "" -or $Only -eq "kb") {
    Write-Host "2. Knowledge Base..." -ForegroundColor Yellow
    $kbFile = Join-Path $From "kb_entries.json"
    if (-not (Test-Path $kbFile)) {
        Write-Host "   kb_entries.json topilmadi -- otkazib yuborildi" -ForegroundColor DarkYellow
    } elseif (-not $KbKey) {
        Write-Host "   -KbKey berilmadi -- KB import otkazib yuborildi" -ForegroundColor DarkYellow
    } else {
        $entries = [System.IO.File]::ReadAllText($kbFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        Write-Host "   $($entries.Count) ta yozuv o'qildi"
        $headers = @{ "X-API-Key" = $KbKey }
        $ok = 0; $fail = 0
        foreach ($e in $entries) {
            if ($e.status -notin @("verified", "active", $null)) { continue }
            $title = if ($e.title) { $e.title } else { $e.query }
            if (-not $title -or -not $e.solution) { continue }
            if ($isDryRun) {
                Write-Host "   [dry-run] POST kb/entries -- $($title.Substring(0, [Math]::Min(50,$title.Length)))"
                $ok++
                continue
            }
            $payload = [ordered]@{
                title    = $title
                solution = $e.solution
                language = if ($e.language) { $e.language } else { "uz" }
                source   = "migration"
                status   = "verified"
                is_shared = if ($null -ne $e.is_shared) { $e.is_shared } else { $false }
            }
            if ($e.description) { $payload["description"] = $e.description }
            try {
                $body = $payload | ConvertTo-Json -Depth 5 -Compress
                $r = Invoke-WebRequest -Uri "$KbApi/kb/entries" -Method Post `
                     -Headers $headers -ContentType "application/json; charset=utf-8" `
                     -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
                     -TimeoutSec 30 -ErrorAction Stop
                if ($r.StatusCode -eq 201) { $ok++ }
            } catch {
                Write-Host "   XATO ($title): $($_.Exception.Message)" -ForegroundColor Red
                $fail++
            }
        }
        Write-Host "   OK: $ok import, $fail xatolik" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Import tugadi!" -ForegroundColor Green
Write-Host ""
