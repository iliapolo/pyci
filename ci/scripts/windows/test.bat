set program=pyci
set DIR=%~dp0:~0,-1%

echo "[test] Starting script"

%DIR%\\install.bat

echo "[test] Running tests"
%PYTHON%\\Scripts\\py.test.exe -c %DIR%\\..\\..\\config\\pytest.init --cov-config=%DIR%\\..\\..\\config\\.coveragerc --cov=pyci %program%/tests || goto :error

echo "[test] Done!"


:error
echo [test] Failed with error #%errorlevel%.
exit /b %errorlevel%