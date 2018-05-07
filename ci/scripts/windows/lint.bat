set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[lint] Starting script"

echo "[lint] Running code analysis"
%PYTHON%\\Scripts\\pylint.exe --rcfile %DIR%\\..\\..\\config\\pylint.ini pyci || goto :error

echo "[lint] Done!"

exit /b 0

:error
echo [lint] Failed with error #%errorlevel%.
exit /b %errorlevel%