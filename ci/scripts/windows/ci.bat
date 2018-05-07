set PATH=%~dp0
set DIR=%PATH:~0,-1%

echo "[ci] Starting script"

call %DIR%\\install.bat || goto :error

call %DIR%\\lint.bat || goto :error

call %DIR%\\test.bat || goto :error

call %DIR%\\codecov.bat || goto :error

call %DIR%\\release.bat || goto :error

echo "[ci] Done"

exit /b 0

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%