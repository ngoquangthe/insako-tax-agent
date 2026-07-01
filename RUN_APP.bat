@echo off
chcp 65001 >nul
echo.
echo ===============================================
echo   AI AGENT KE TOAN - THUE - INSAKO
echo   Web App dang khoi dong...
echo ===============================================
echo.

:: Lay dia chi IP noi bo de hien thi cho nhan vien
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%

echo Mo trinh duyet tai:
echo   May tinh nay  : http://localhost:8501
echo   Noi bo cong ty: http://%IP%:8501
echo.
echo Chia se dia chi http://%IP%:8501 cho nhan vien cung mang LAN.
echo Nhan Ctrl+C de dung app.
echo.

cd /d "%~dp0"
python -m streamlit run app.py ^
    --server.port 8501 ^
    --server.address 0.0.0.0 ^
    --browser.gatherUsageStats false ^
    --server.headless true
pause
