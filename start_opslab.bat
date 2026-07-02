@echo off
cd /d D:\CSI\opslab-ai\opslab-ai

echo Uruchamianie OpsLab AI...
echo.

start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8502"

.\.venv\Scripts\python.exe -m streamlit run dashboard\streamlit_app.py --server.address 127.0.0.1 --server.port 8502

pause