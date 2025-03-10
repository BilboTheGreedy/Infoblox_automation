#!/usr/bin/env python3
"""
Setup configuration for Infoblox Mock Server package
"""

from setuptools import setup, find_packages
import os
import re

# Read the version from the __init__.py file
with open(os.path.join('infoblox_mock', '__init__.py'), 'r') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    version = version_match.group(1) if version_match else '0.1.0'

# Read the long description from README.md
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='infoblox_mock_server',
    version=version,
    description='A comprehensive mock server for Infoblox WAPI',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Daniel Rapp',
    author_email='daniel.rapp@live.se',
    url='https://github.com/bilbothegreedy/infoblox-mock-server',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask>=2.0.0',
        'Werkzeug>=2.0.0',
        'requests>=2.25.0',
        'ipaddress>=1.0.23',
        'python-dateutil>=2.8.2',
    ],
    entry_points={
        'console_scripts': [
            'infoblox-mock-server=run_server:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development :: Testing',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    python_requires='>=3.6',
)