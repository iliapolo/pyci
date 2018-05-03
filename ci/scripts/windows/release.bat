set DIR=%~dp0:~0,-1%

echo "[release] Starting script"

%DIR%\\install.bat

echo "[release] Running release"
%PYTHON%\\Scripts\\pyci.exe --debug release --pypi-test || goto :error

echo "[release] Done!"


:error
echo [release] Failed with error #%errorlevel%.
exit /b %errorlevel%