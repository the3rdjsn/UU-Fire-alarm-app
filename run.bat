@echo off
echo.
echo  UofU Fire Alarm Management System
echo  University of Utah -- Facilities Management
echo  ------------------------------------------
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found.
    echo Download and install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Installing / verifying dependencies...
python -m pip install streamlit pandas plotly openpyxl --quiet

echo.
echo  Starting at http://localhost:8501
echo  Press Ctrl+C to stop
echo.

python -m streamlit run app.py ^
    --server.port 8501 ^
    --browser.gatherUsageStats false ^
    --theme.primaryColor "#CC2929" ^
    --theme.backgroundColor "#ffffff" ^
    --theme.secondaryBackgroundColor "#f8f8f8" ^
    --theme.textColor "#1a1a1a"

pause
