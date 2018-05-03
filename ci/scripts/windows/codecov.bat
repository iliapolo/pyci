set program=pyci
set DIR=%~dp0:~0,-1%

echo "[codecov] Starting script"

%DIR%\\install.bat

echo "[codecov] Uploading code coverage..."
%PYTHON%\\Scripts\\codecov.exe || goto :error

echo "[codecov] Done!"


:error
echo [codecov] Failed with error #%errorlevel%.
exit /b %errorlevel%