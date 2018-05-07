set PATH=%~dp0
set DIR=%PATH:~0,-1%
set PWD=%cd%

echo "[test] Starting script"

rem call :create_wheel wheel_path

rem call :create_binary binary_path

echo "[test] Running source tests"
%PYTHON%\\python.exe -m pip uninstall -y py-ci || goto :error
%PYTHON%\\python.exe -m pip install %DIR%\\..\\..\\..\\. || goto :error
set PYCI_TEST_PACKAGE=source
%PYTHON%\\Scripts\\py.test.exe --cov-append -c %DIR%\\..\\..\\config\\pytest.ini --cov-config=%DIR%\\..\\..\\config\\coverage.ini --cov=pyci pyci/tests || goto :error

rem echo "[test] Running wheel tests"
rem %PYTHON%\\python.exe -m pip uninstall -y py-ci || goto :error
rem %PYTHON%\\python.exe -m pip install %wheel_path% || goto :error
rem set PYCI_TEST_PACKAGE=wheel
rem set PYCI_EXECUTABLE_PATH=%PYTHON%\\Scripts\\pyci.exe
rem %PYTHON%\\Scripts\\py.test.exe -rs --cov-append -c %DIR%\\..\\..\\config\\pytest.ini --cov-config=%DIR%\\..\\..\\config\\coverage.ini --cov=pyci pyci/tests || goto :error
rem
rem echo "[test] Running binary tests"
rem %PYTHON%\\python.exe -m pip uninstall -y py-ci || goto :error
rem set PYCI_TEST_PACKAGE=binary
rem set PYCI_EXECUTABLE_PATH=%binary_path%
rem %PYTHON%\\Scripts\\py.test.exe -rs --cov-append -c %DIR%\\..\\..\\config\\pytest.ini --cov-config=%DIR%\\..\\..\\config\\coverage.ini --cov=pyci pyci/tests || goto :error


echo "[test] Done!"

exit /b 0

:create_wheel
%PYTHON%\\Scripts\\pyci.exe pack --path %DIR%\\..\\..\\..\\ wheel || goto :error
exit /b 0

:create_binary
%PYTHON%\\Scripts\\pyci.exe pack --path %DIR%\\..\\..\\..\\ binary || goto :error
exit /b 0

:error
echo [test] Failed with error #%errorlevel%.
exit /b %errorlevel%
