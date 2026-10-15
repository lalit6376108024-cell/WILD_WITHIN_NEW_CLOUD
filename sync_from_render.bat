@echo off
setlocal
if "%WILD_WITHIN_URL%"=="" (
  echo Set WILD_WITHIN_URL to your Render app URL first.
  exit /b 1
)
if "%SYNC_TOKEN%"=="" (
  echo Set SYNC_TOKEN to the same secret configured in Render first.
  exit /b 1
)
python tools\sync_cloud_to_pc.py
if errorlevel 1 exit /b %errorlevel%
endlocal
