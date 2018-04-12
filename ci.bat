set program=pyci

echo "Installing test requirements"
%PYTHON%\\python.exe -m pip install -r test-requirements.txt || goto :error

echo "Installing dependencies"
%PYTHON%\\python.exe -m pip install -e . || goto :error

echo "Running code analysis"
%PYTHON%\\Scripts\\pylint.exe --rcfile .pylint.ini %program% || goto :error

echo "Running tests"
%PYTHON%\\Scripts\\py.test.exe --cov-report term-missing --cov=%program% %program%/tests || goto :error

echo "Running release"
%PYTHON%\\Scripts\\%program%.exe release create || goto :error

echo "Done!"


:error
echo Failed with error #%errorlevel%.
exit /b %errorlevel%