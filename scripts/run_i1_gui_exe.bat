@echo off
setlocal

pushd "%~dp0\.."

if not exist "dist\i1-gui-exe\worldzero-i1-playable-gui.exe" (
  echo [run] exe ?? ??????. ??????? ?????????: scripts\build_i1_gui_exe.bat
  popd
  exit /b 1
)

"dist\i1-gui-exe\worldzero-i1-playable-gui.exe" %*
popd
