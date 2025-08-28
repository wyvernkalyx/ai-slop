@echo off
echo ========================================
echo    RESTARTING AI-SLOP WITH UPDATES
echo ========================================
echo.
echo Killing any existing Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Clearing browser cache reminder:
echo - Press Ctrl+F5 in browser to force refresh
echo - Or open in incognito/private window
echo.

echo Starting enhanced app v1.2.1 (Custom Voice Fix)...
echo.
echo Opening browser at http://localhost:5000
echo.
timeout /t 2 /nobreak >nul
start http://localhost:5000
echo.
echo Starting server...
python app_enhanced.py
pause