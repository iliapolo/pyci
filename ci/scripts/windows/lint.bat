set program=pyci
set DIR=%~dp0:~0,-1%

echo "[lint] Starting script"

%DIR%\\install.bat

echo "[lint] Running code analysis"
%PYTHON%\\Scripts\\pylint.exe --rcfile %DIR%\\..\\..\\config\\pylint.ini %program% || goto :error

echo "[lint] Done!"


:error
echo [lint] Failed with error #%errorlevel%.
exit /b %errorlevel%