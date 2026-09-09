@echo off
setlocal

set "ROOT=%~dp0\.."
pushd "%ROOT%"

set "ENTRY=play_pilot_i1.py"
set "OUTDIR=dist\i1-exe"
set "WORKDIR=build\pyinstaller"
set "NAME=worldzero-i1-playable"
set "PYTHON=py"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo [build] PyInstaller не найден. Устанавливаю в текущее окружение...
  %PYTHON% -m pip install pyinstaller
  if errorlevel 1 (
    echo [build] Не удалось установить PyInstaller.
    popd
    exit /b 1
  )
)

%PYTHON% -m PyInstaller --onefile --clean --noconfirm --name "%NAME%" --distpath "%OUTDIR%" --workpath "%WORKDIR%" --specpath "%WORKDIR%" "%ENTRY%"
set "RES=%ERRORLEVEL%"
if not "%RES%"=="0" (
  popd
  exit /b %RES%
)

echo [build] Готово: %OUTDIR%\%NAME%.exe
popd
exit /b 0
