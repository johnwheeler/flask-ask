"""
Flask-Ask
-------------

Easy Alexa Skills Kit integration for Flask
"""
from setuptools import setup


setup(
    name='Flask-Ask',
    version='0.5',
    url='https://github.com/johnwheeler/flask-ask',
    license='MIT',
    author='John Wheeler',
    author_email='john@johnwheeler.org',
    description='Rapid Alexa Skills Kit Development for Amazon Echo Devices in Python',
    long_description=__doc__,
    packages=['flask_ask'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask',
        'pyOpenSSL',
        'PyYAML',
        'aniso8601'
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Framework :: Flask',
        'Programming Language :: Python',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
