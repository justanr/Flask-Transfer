from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    # Taken from py.test setuptools integration page
    # http://pytest.org/latest/goodpractices.html

    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finialize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


if __name__ == "__main__":
    setup(
        name='flask-transfer',
        version='0.0.1',
        author='Alec Nikolas Reiter',
        author_email='alecreiter@gmail.com',
        description='Validate and process file uploads in Flask easily',
        license='MIT',
        packages=['flask_transfer'],
        zip_safe=False,
        url="https://github.com/justanr/Flask-Transfer",
        keywords=['flask', 'uploads'],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Framework :: Flask',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.4'
        ],
        install_requires=['Flask'],
        test_suite='test',
        tests_require=['pytest'],
        cmdclass={'test': PyTest},
    )
