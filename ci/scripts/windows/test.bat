set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[test] Starting script"

CALL %DIR%\\install.bat

echo "[test] Running tests"
%PYTHON%\\Scripts\\py.test.exe -c %DIR%\\..\\..\\config\\pytest.init --cov-config=%DIR%\\..\\..\\config\\.coveragerc --cov=pyci pyci/tests || goto :error

echo "[test] Done!"


:error
echo [test] Failed with error #%errorlevel%.
exit /b %errorlevel%