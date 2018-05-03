set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[ci] Starting script"

git status

CALL %DIR%\\install.bat || goto :error

CALL %DIR%\\lint.bat || goto :error

CALL %DIR%\\test.bat || goto :error

CALL %DIR%\\codecov.bat || goto :error

CALL %DIR%\\release.bat || goto :error

echo "[ci] Done"

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%