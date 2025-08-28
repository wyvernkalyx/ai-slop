# PowerShell script to restart AI-Slop with updates

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   RESTARTING AI-SLOP WITH UPDATES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Killing any existing Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "IMPORTANT - Clear browser cache:" -ForegroundColor Red
Write-Host "- Press Ctrl+F5 in browser to force refresh" -ForegroundColor White
Write-Host "- Or open in incognito/private window" -ForegroundColor White
Write-Host ""

Write-Host "Starting enhanced app v1.2.1 (Custom Voice Fix)..." -ForegroundColor Green
Write-Host ""

# Open browser
Write-Host "Opening browser at http://localhost:5000" -ForegroundColor Cyan
Start-Sleep -Seconds 1
Start-Process "http://localhost:5000"

Write-Host ""
Write-Host "Starting server..." -ForegroundColor Green
python app_enhanced.py