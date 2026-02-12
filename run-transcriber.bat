@echo off
if not defined SILENT (
  start /min "" cmd /c "set SILENT=1 && "%~f0" %*"
  exit /b
)

setlocal

REM Change to the script directory
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)


REM Prefer pythonw to avoid a console window for the GUI app
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "" /b pythonw main.py
) else (
  start "" /b pythonw main.py
)

set EXITCODE=%ERRORLEVEL%
popd
endlocal & exit /b %EXITCODE%
