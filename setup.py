"""
subdown
----------

subdown is a tool for downloading images from reddit.
"""

from setuptools import setup, find_packages
from subdown import NAME, VERSION, SHORT_DESC

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email='jc@blackflags.co.uk',
    packages=find_packages(),
    url='http://pypi.python.org/pypi/suave/',
    license='LICENSE.txt',
    description=SHORT_DESC,
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
