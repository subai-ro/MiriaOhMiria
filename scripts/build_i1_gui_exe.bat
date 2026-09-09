@echo off
setlocal

set "ROOT=%~dp0\.."
pushd "%ROOT%"

set "ENTRY=play_pilot_i1_gui.py"
set "OUTDIR=dist\i1-gui-exe"
set "WORKDIR=build\pyinstaller-gui"
set "NAME=worldzero-i1-playable-gui"
set "PYTHON=py"

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo [build] PyInstaller ?? ??????. ???????????? ? ??????? ?????????...
  %PYTHON% -m pip install pyinstaller
  if errorlevel 1 (
    echo [build] ?? ??????? ?????????? PyInstaller.
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

echo [build] ??????: %OUTDIR%\%NAME%.exe
popd
exit /b 0
