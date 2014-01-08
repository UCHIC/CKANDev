from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-Metadata',
    version=version,
    description="expand metadata for iUtah requirements",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Stephanie Reeder',
    author_email='stephanie.reeder@usu.edu',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.Metadata'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        iutahmetadata=ckanext.Metadata.plugin:MetadataPlugin
        # Add plugins here, e.g.
        # myplugin=ckanext.Metadata.plugin:PluginClass
    ''',
)
