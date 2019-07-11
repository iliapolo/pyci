

def get_args():

    setup_py = """
from setuptools import setup

setup(
    name='q',
    license='LICENSE',
    version='2.0.5',
    author='Harel Ben-Attia',
    author_email='harelba@gmail.com',
    install_requires=[
        'six==1.11.0'
    ],
    packages=[
        'q'
    ],
    entry_points={
        'console_scripts': [
            'q = q.q:run_standalone'
        ]
    }
)
    
    """

    kw = {}

    def _setup(*args, **kwargs):
        kw.update(kwargs)
        return kwargs

    import setuptools

    setuptools.setup = _setup

    q = compile(setup_py, '/tmp/test-setup.runtime', mode='exec')

    eval(q)

    print kw


get_args()
