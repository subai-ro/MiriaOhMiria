@echo off
setlocal

pushd "%~dp0\.."

if not exist "dist\i1-exe\worldzero-i1-playable.exe" (
  echo [run] exe not found. Build first: scripts\build_i1_exe.bat
  popd
  exit /b 1
)

"dist\i1-exe\worldzero-i1-playable.exe" %*
popd
