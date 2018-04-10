set program=pyci

dir %PYTHON%\\Scripts
echo "Installing test requirements"
%PYTHON%\\python.exe -m pip install -r test-requirements.txt || goto :error

dir %PYTHON%\\Scripts
echo "Installing dependencies"
%PYTHON%\\python.exe -m pip install -e . || goto :error

dir %PYTHON%\\Scripts
echo "Running code analysis"
%PYTHON%\\Scripts\\pylint.exe --rcfile .pylint.ini %program% || goto :error

dir %PYTHON%\\Scripts
echo "Running tests"
%PYTHON%\\Scripts\\py.test.exe --cov-report term-missing --cov=%program% %program%/tests || goto :error

dir %PYTHON%\\Scripts
echo "Running release"
%PYTHON%\\Scripts\\%program%.exe --repo iliapolo/%program% releaser release --branch release--binary-entrypoint pyci.spec || goto :error

dir %PYTHON%\\Scripts
echo "Done!"


:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%