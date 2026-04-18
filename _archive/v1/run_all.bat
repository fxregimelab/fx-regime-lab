@echo off
:: run_all.bat
:: Runs the full fx_regime pipeline and deploys the brief.
:: Schedule this via Windows Task Scheduler at 17:30 NY (23:30 CET / next-day 05:00 IST)
:: to ensure latest.csv always reflects yesterday's close data.
::
:: Task Scheduler setup:
::   Action:  Start a program
::   Program: C:\Market Journey 2026\Code\fx_regime\run_all.bat
::   Start in: C:\Market Journey 2026\Code\fx_regime
::   Trigger: Daily at 17:30 (Eastern Time)

cd /d "%~dp0"

:: Build a datestamp for the log filename (YYYYMMDD)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set LOGDATE=%DT:~0,8%
set LOGFILE=runs\%LOGDATE%\bat_runner.log

:: Ensure runs folder exists early so we can write the log
if not exist "runs\%LOGDATE%" mkdir "runs\%LOGDATE%"

echo ============================================================  >> "%LOGFILE%"
echo  G10 FX REGIME PIPELINE  --  %DATE% %TIME%                    >> "%LOGFILE%"
echo ============================================================  >> "%LOGFILE%"

echo ============================================================
echo  G10 FX REGIME PIPELINE  --  %DATE% %TIME%
echo ============================================================

:: Activate virtual environment if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [INFO] activated .venv
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [INFO] activated venv
) else (
    echo [INFO] No venv found, using system Python
)

:: Run the full pipeline via run.py (has per-step logging + pipeline.log)
python run.py >> "%LOGFILE%" 2>&1

set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
    echo.
    echo [ERROR] Pipeline failed with exit code %EXITCODE% -- see %LOGFILE%  >> "%LOGFILE%"
    echo [ERROR] Pipeline failed with exit code %EXITCODE% -- see %LOGFILE%
    exit /b %EXITCODE%
)

echo.
echo ============================================================
echo  Pipeline complete  --  %DATE% %TIME%                         >> "%LOGFILE%"
echo ============================================================  >> "%LOGFILE%"
echo  Pipeline complete  --  %DATE% %TIME%
echo ============================================================
