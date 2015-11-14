from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys
import re
import ast


def _get_version():
    version_re = re.compile(r'__version__\s+=\s+(.*)')

    with open('flask_transfer/__init__.py', 'rb') as fh:
        version = ast.literal_eval(
            version_re.search(fh.read().decode('utf-8')).group(1))

    return str(version)


class ToxTest(TestCommand):
    user_options = [('tox-args=', 'a', 'Arguments to pass to tox')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox
        import shlex
        args = []
        if self.tox_args:
            args = shlex.split(self.tox_args)

        errno = tox.cmdline(args=args)
        sys.exit(errno)


if __name__ == "__main__":
    setup(
        name='flask-transfer',
        version=_get_version(),
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
        tests_require=['tox'],
        cmdclass={'tox': ToxTest},
    )
