"""
Flask-Ask
-------------

Easy Alexa Skills Kit integration for Flask
"""
from setuptools import setup


setup(
    name='Flask-Ask',
    version='0.2',
    url='https://github.com/johnwheeler/flask-ask',
    license='BSD',
    author='John Wheeler',
    author_email='john@bookkeeper.io',
    description='Easy Alexa Skills Kit integration for Flask',
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
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
