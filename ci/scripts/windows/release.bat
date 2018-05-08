set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[release] Starting script"

echo "[release] Running release"
dir %PYTHON%\\Scripts
%PYTHON%\\Scripts\\pyci.exe --debug release --pypi-test || goto :error

echo "[release] Done!"

exit /b 0

:error
echo [release] Failed with error #%errorlevel%.
exit /b %errorlevel%