set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[install] Starting script"

echo "[install] Installing test requirements"
%PYTHON%\\python.exe -m pip install -r %DIR%\\..\\..\\..\\test-requirements.txt || goto :error

echo "[install ]Installing dependencies"
%PYTHON%\\python.exe -m pip install -e %DIR%\\..\\..\\..\\. || goto :error
%PYTHON%\\python.exe -m pip install https://github.com/iliapolo/PyGithub/archive/upload-asset-temp.zip

echo "[install] Done!"


:error
echo [install] Failed with error #%errorlevel%.
exit /b %errorlevel%