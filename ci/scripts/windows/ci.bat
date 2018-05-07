set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[ci] Starting script"

CALL %DIR%\\install.bat || goto :error

CALL %DIR%\\lint.bat || goto :error

REM CALL %DIR%\\test.bat || goto :error

REM CALL %DIR%\\codecov.bat || goto :error

REM CALL %DIR%\\release.bat || goto :error

echo "[ci] Done"

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%