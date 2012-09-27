"""
subdown
----------

subdown is a tool for downloading images from reddit.
"""

from setuptools import setup, find_packages
from subdown import NAME, VERSION, AUTHOR, SHORT_DESC

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email='jc@blackflags.co.uk',
    url='https://github.com/radiosilence/subdown',
    license='LICENSE.txt',
    description=SHORT_DESC,
    long_description=open('README.rst').read(),
    install_requires=open('requirements.txt').read().split("\n"),
    package_data={
        '': ['*.txt', '*.rst']
    },
    include_package_data=True,
    py_modules=['subdown'],
    scripts=['scripts/subdown'],
)
