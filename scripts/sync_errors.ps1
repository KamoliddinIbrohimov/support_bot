# ─────────────────────────────────────────────────────────────────────────────
# sync_errors.ps1  —  Lokal error bazasini serverga sinxronlashtirish
#
# Foydalanish:
#   .\sync_errors.ps1 -ServerUrl "http://SERVER_IP:8000"
#   .\sync_errors.ps1 -ServerUrl "http://SERVER_IP:8000" -DryRun
#
# Nima qiladi:
#   1. Lokal API dan barcha xatoliklarni oladi
#   2. Server API dan mavjud xatoliklarni oladi
#   3. Serverde YO'Q bo'lgan xatoliklarni yuklaydi (title_ru bo'yicha)
# ─────────────────────────────────────────────────────────────────────────────
param(
    [string]$LocalUrl   = "http://localhost:8000",
    [string]$ServerUrl  = "",
    [switch]$DryRun
)

if (-not $ServerUrl) {
    Write-Host "❌ Server URL kerak!" -ForegroundColor Red
    Write-Host "   Misol: .\sync_errors.ps1 -ServerUrl `"http://1.2.3.4:8000`""
    exit 1
}

$ServerUrl = $ServerUrl.TrimEnd("/")
$LocalUrl  = $LocalUrl.TrimEnd("/")

Write-Host ""
Write-Host "🔄 Error bazasini sinxronlashtirish" -ForegroundColor Cyan
Write-Host "   Lokal : $LocalUrl"
Write-Host "   Server: $ServerUrl"
if ($DryRun) { Write-Host "   [DRY RUN — hech narsa yuborilmaydi]" -ForegroundColor Yellow }
Write-Host ""

# ── 1. Lokaldan xatoliklarni olish ───────────────────────────────────────────
Write-Host "📥 Lokal xatoliklarni yuklanmoqda..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$LocalUrl/errors" -UseBasicParsing -TimeoutSec 10
    $localErrors = ($resp.Content | ConvertFrom-Json)
    Write-Host " $($localErrors.Count) ta" -ForegroundColor Green
} catch {
    Write-Host " XATOLIK: $_" -ForegroundColor Red
    exit 1
}

if ($localErrors.Count -eq 0) {
    Write-Host "ℹ️  Lokal bazada xatolik yo'q. Tugadi."
    exit 0
}

# ── 2. Serverdan mavjud xatoliklarni olish ────────────────────────────────────
Write-Host "📡 Server xatoliklarini tekshirmoqda..." -NoNewline
try {
    $resp = Invoke-WebRequest -Uri "$ServerUrl/errors" -UseBasicParsing -TimeoutSec 10
    $serverErrors = ($resp.Content | ConvertFrom-Json)
    Write-Host " $($serverErrors.Count) ta" -ForegroundColor Green
} catch {
    Write-Host " XATOLIK: $_" -ForegroundColor Red
    Write-Host "   Server API ga ulanib bo'lmadi. URL to'g'rimi?"
    exit 1
}

# ── 3. Qaysilari yo'qligini aniqlash (title_ru bo'yicha) ─────────────────────
$serverTitles = @{}
foreach ($e in $serverErrors) {
    if ($e.title_ru) { $serverTitles[$e.title_ru.Trim()] = $true }
}

$toUpload = @()
foreach ($e in $localErrors) {
    $key = if ($e.title_ru) { $e.title_ru.Trim() } else { $e.title }
    if (-not $serverTitles.ContainsKey($key)) {
        $toUpload += $e
    }
}

Write-Host ""
if ($toUpload.Count -eq 0) {
    Write-Host "✅ Server allaqachon to'liq sinxron. Yangi xatolik yo'q." -ForegroundColor Green
    exit 0
}

Write-Host "📋 Yuklash kerak: $($toUpload.Count) ta yangi xatolik" -ForegroundColor Yellow
foreach ($e in $toUpload) {
    $title = if ($e.title_ru) { $e.title_ru } else { $e.title }
    Write-Host "   + $title"
}
Write-Host ""

if ($DryRun) {
    Write-Host "🔍 DRY RUN tugadi. Hech narsa yuborilmadi." -ForegroundColor Yellow
    exit 0
}

# ── 4. Yangi xatoliklarni serverga yuklash ───────────────────────────────────
$ok = 0
$fail = 0

foreach ($e in $toUpload) {
    $title = if ($e.title_ru) { $e.title_ru } else { $e.title }

    # Keywords ni array ko'rinishiga keltirish
    $kw = if ($e.keywords_ru) { $e.keywords_ru } elseif ($e.keywords) { $e.keywords } else { @() }

    $body = @{
        title        = $title
        keywords     = $kw
        solution     = if ($e.solution_ru) { $e.solution_ru } elseif ($e.solution) { $e.solution } else { "" }
        title_ru     = $e.title_ru
        title_uz     = $e.title_uz
        keywords_ru  = $kw
        keywords_uz  = if ($e.keywords_uz) { $e.keywords_uz } else { $kw }
        solution_ru  = $e.solution_ru
        solution_uz  = $e.solution_uz
    } | ConvertTo-Json -Depth 5

    try {
        $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
        $resp = Invoke-WebRequest `
            -Uri "$ServerUrl/errors" `
            -Method POST `
            -Body $bodyBytes `
            -ContentType "application/json; charset=utf-8" `
            -UseBasicParsing `
            -TimeoutSec 15
        $ok++
        Write-Host "   ✅ $title" -ForegroundColor Green
    } catch {
        $fail++
        Write-Host "   ❌ $title — $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "─────────────────────────────────────" -ForegroundColor Cyan
Write-Host "✅ Yuklandi : $ok ta" -ForegroundColor Green
if ($fail -gt 0) {
    Write-Host "❌ Xatolik  : $fail ta" -ForegroundColor Red
}
Write-Host ""
