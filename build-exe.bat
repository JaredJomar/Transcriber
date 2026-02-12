@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
  ) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
      set "PYTHON_EXE=python"
    )
  )
)

if not defined PYTHON_EXE (
  echo [ERROR] Python was not found. Install Python 3.10+ and retry.
  popd >nul
  exit /b 1
)

echo [1/3] Installing build dependencies...
call "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --upgrade pip
if errorlevel 1 goto :fail
call "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [2/3] Building one-file executable...
if exist "build" rmdir /s /q "build"
if exist "dist\Transcriber" rmdir /s /q "dist\Transcriber"
if exist "dist\Transcriber.exe" del /q "dist\Transcriber.exe"

call "%PYTHON_EXE%" %PYTHON_ARGS% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "Transcriber" ^
  --icon "icons\app_icon.ico" ^
  --add-data "icons;icons" ^
  --collect-all "whisper" ^
  --collect-all "yt_dlp" ^
  main.py
if errorlevel 1 goto :fail

echo [3/3] Done.
echo Output: dist\Transcriber.exe
popd >nul
exit /b 0

:fail
echo [ERROR] Build failed.
popd >nul
exit /b 1
