# Script khoi chay PostgreSQL 15 container cho BudgetBot
$ErrorActionPreference = "Stop"

Write-Host "=== Kiem tra Docker tren may ===" -ForegroundColor Cyan
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Docker chua duoc cai dat hoac chua duoc them vao PATH." -ForegroundColor Yellow
    $installer = "$env:USERPROFILE\Downloads\Docker Desktop Installer.exe"
    if (Test-Path $installer) {
        Write-Host "[i] Da tim thay file cai dat tai: $installer" -ForegroundColor Green
        Write-Host "[*] Vui long cai dat Docker Desktop va khoi chay ung dung truoc khi bat container." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "[*] Dang khoi chay PostgreSQL 15 container qua docker compose..." -ForegroundColor Cyan
docker compose up -d

Write-Host "[*] Dang doi PostgreSQL san sang (port 5432)..." -ForegroundColor Cyan
$maxRetries = 15
$retry = 0
$ready = $false

while ($retry -lt $maxRetries) {
    Start-Sleep -Seconds 2
    $tcp = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue
    if ($tcp.TcpTestSucceeded) {
        $ready = $true
        break
    }
    $retry++
    Write-Host "  ... dang kiem tra ket noi (lan $retry/$maxRetries)"
}

if ($ready) {
    Write-Host "[v] PostgreSQL 15 container da hoat dong tai localhost:5432" -ForegroundColor Green
    Write-Host "[v] Database 'budgetbot' da duoc tu dong khoi tao!" -ForegroundColor Green
} else {
    Write-Host "[!] Container da bat nhung port 5432 chua san sang. Kiem tra log: docker compose logs db" -ForegroundColor Red
}
