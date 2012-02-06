"""
subdown.py
----------

subdown.py is a tool for downloading images from reddit.
"""

from setuptools import setup, find_packages

setup(
    name='suave',
    version='0.1',
    author='James Cleveland',
    author_email='jc@blackflags.co.uk',
    packages=find_packages(),
    url='http://pypi.python.org/pypi/suave/',
    license='LICENSE.txt',
    description='A tool for downloading images from reddit.',
    long_description=open('README.rst').read(),
    install_requires=open('requirements.txt').read().split("\n"),
    package_data={
        '': ['*.txt', '*.rst']
    },
    entry_points = {
        'console_scripts': [
            'subdown = subdown:main'
        ],
    }
)
