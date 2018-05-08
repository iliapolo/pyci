set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[codecov] Starting script"

echo "[codecov] Creating coverage xml..."
%PYTHON%\\Scripts\\coverage.exe xml -i

echo "[codecov] Uploading code coverage..."
%PYTHON%\\Scripts\\codecov.exe -f coverage.xml || goto :error

echo "[codecov] Done!"

exit /b 0

:error
echo [codecov] Failed with error #%errorlevel%.
exit /b %errorlevel%