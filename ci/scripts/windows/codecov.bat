set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[codecov] Starting script"

CALL %DIR%\\install.bat

echo "[codecov] Creating coverage xml..."
%PYTHON%\\Scripts\\coverage xml -i

echo "[codecov] Uploading code coverage..."
%PYTHON%\\Scripts\\codecov.exe || goto :error

echo "[codecov] Done!"


:error
echo [codecov] Failed with error #%errorlevel%.
exit /b %errorlevel%