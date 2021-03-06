from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(
    name='ckanext-mdftemplate',
    version=version,
    description="Template extension for MDF iUtah.",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Juan Caraballo',
    author_email='juan.caraballo17@gmail.com',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.mdftemplate'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        mdftemplate=ckanext.mdftemplate.plugin:MdfThemePlugin
    ''',
)
