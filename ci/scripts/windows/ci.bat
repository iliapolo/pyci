set DIR=%~dp0:~0,-1%

echo "[ci] Starting script"

echo %DIR%

%DIR%\\install.bat

%DIR%\\lint.bat

%DIR%\\test.bat

%DIR%\\codecov.bat

%DIR%\\release.bat

echo "[ci] Done"

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%