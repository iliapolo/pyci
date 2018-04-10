
program=pyci

dir %PYTHON%
echo "Installing test requirements"
%PYTHON%\\python.exe -m pip install -r test-requirements.txt

dir %PYTHON%
echo "Installing dependencies"
%PYTHON%\\python.exe -m pip install -e .

dir %PYTHON%
echo "Running code analysis"
%PYTHON%\\pylint.exe --rcfile .pylint.ini ${program}

dir %PYTHON%
echo "Running tests"
%PYTHON%\\py.test.exe --cov-report term-missing --cov=${program} ${program}/tests

dir %PYTHON%
echo "Running release"
%PYTHON%\\${program}.exe --repo iliapolo/${program} releaser release --branch release --binary-entrypoint pyci.spec

dir %PYTHON%
echo "Done!"