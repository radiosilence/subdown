"""
subdown
----------

subdown is a tool for downloading images from reddit.
"""
from setuptools import setup

setup(
    name='subdown',
    version='0.2.2',
    author='James Cleveland',
    author_email='jc@blackflags.co.uk',
    url='https://github.com/radiosilence/subdown',
    license='LICENSE.txt',
    description='Reddit image scraper',
    long_description=open('README.rst').read(),
    install_requires=open('requirements.txt').read().split("\n"),
    package_data={
        '': ['*.txt', '*.rst']
    },
    include_package_data=True,
    py_modules=['subdown'],
    scripts=['scripts/subdown'],
)
