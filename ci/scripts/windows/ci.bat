set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[ci] Starting script"

%DIR%\\install.bat || goto :error

%DIR%\\lint.bat || goto :error

%DIR%\\test.bat || goto :error

%DIR%\\codecov.bat || goto :error

%DIR%\\release.bat || goto :error

echo "[ci] Done"

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%