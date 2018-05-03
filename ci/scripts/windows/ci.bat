set DIR=%~dp0:~0,-1%
set DIR2=%0
set DIR3=%~dp0
set DIR4=%DIR3:~0,-1%

echo "[ci] Starting script"

echo %DIR%
echo %DIR2%
echo %DIR3%
echo %DIR4%

%DIR%\\install.bat

%DIR%\\lint.bat

%DIR%\\test.bat

%DIR%\\codecov.bat

%DIR%\\release.bat

echo "[ci] Done"

:error
echo [ci] Failed with error #%errorlevel%.
exit /b %errorlevel%