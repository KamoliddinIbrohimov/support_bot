# Docker tayyor bo'lguncha kutish va servislarni ishga tushirish
$projectDir = "C:\Users\QA\Desktop\support"
$logFile = "$projectDir\startup.log"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Write-Log "=== Servislarni ishga tushirish boshlandi ==="

# Docker Desktop tayyor bo'lguncha kutish (max 5 daqiqa)
$maxWait = 300
$waited = 0
Write-Log "Docker tayyor bo'lguncha kutilmoqda..."

while ($waited -lt $maxWait) {
    try {
        $result = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker tayyor."
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
    $waited += 5
    Write-Log "Kutilmoqda... ($waited/$maxWait s)"
}

if ($waited -ge $maxWait) {
    Write-Log "XATO: Docker $maxWait soniya ichida tayyor bo'lmadi."
    exit 1
}

# Servislarni ishga tushirish
Set-Location $projectDir
Write-Log "docker-compose up -d ishga tushirilmoqda..."
$output = docker-compose up -d 2>&1
Write-Log $output

# Admin panel alohida
Write-Log "Admin panel ishga tushirilmoqda..."
Set-Location "$projectDir\admin-panel"
$output = docker-compose up -d 2>&1
Write-Log $output

Write-Log "=== Hammasi ishga tushdi ==="
