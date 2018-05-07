set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[test] Starting script"

call %DIR%\\install.bat

set COMMAND="%PYTHON%\\Scripts\\py.test.exe -c %DIR%\\..\\..\\config\\pytest.ini --cov-config=%DIR%\\..\\..\\config\\coverage.ini --cov=pyci pyci/tests"

echo "[test] Running source tests"
%PYTHON%\\python.exe -m pip uninstall -y py-ci || goto :error
%PYTHON%\\python.exe -m pip install %DIR%\\..\\..\\..\\. || goto :error
set PYCI_TEST_PACKAGE=source
$COMMAND% || goto :error

echo "[test] Done!"


:error
echo [test] Failed with error #%errorlevel%.
exit /b %errorlevel%