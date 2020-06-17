"""
Flask-Ask
-------------

Easy Alexa Skills Kit integration for Flask
"""
from setuptools import setup

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

setup(
    name='Flask-Ask',
    version='0.9.7',
    url='https://github.com/johnwheeler/flask-ask',
    license='Apache 2.0',
    author='John Wheeler',
    author_email='john@johnwheeler.org',
    description='Rapid Alexa Skills Kit Development for Amazon Echo Devices in Python',
    long_description=__doc__,
    packages=['flask_ask'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=parse_requirements('requirements.txt'),
    test_requires=[
        'mock',
        'requests'
    ],
    test_suite='tests',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Framework :: Flask',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
