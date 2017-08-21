"""TODO: module doc..."""

import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='panelapp',
    version='2.0.5',
    author='Antonio Rueda-Martin,Oleg Gerasimenko',
    author_email='antonio.rueda-martin@genomicsengland.co.uk,oleg.gerasimenko@genomicsengland.co.uk',
    url='https://github.com/genomicsengland/PanelApp2',
    description='PanelApp',
    license='Internal GEL use only',  # example license
    classifiers=[
        'Environment :: Other Environment',
        'Intended Audience :: Other Audience',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering',
    ],
    packages=find_packages(),
    include_package_data=True,
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest==3.0.7',
        'pytest-django==3.1.2',
        'flake8==3.3.0',
        'faker==0.7.12',
        'factory_boy==2.8.1',
    ],
    install_requires=[
        'django==1.11.4',
        'simplejson==3.8.2',
        'psycopg2==2.7.3',
        'dj-database-url==0.4.2',
        'django-model-utils==3.0.0',
        'djangoajax==2.3.7',
        'djangorestframework==3.6.3',
        'django-tables2==1.6.1',
        'django-filter==1.0.4',
        'django-cors-headers==2.0.2',
        'django-autocomplete-light==3.2.7',
        'django-model-utils==3.0.0',
        'django-markdown-deux==1.0.5',
        'django-bootstrap3==9.0.0',
        'django-markdownx==2.0.21',
        'django-object-actions==0.10.0',
        'django-mathfilters==0.4.0',
        'celery==4.1.0',
        'more-itertools==3.2.0',
        'requests==2.18.2',
        'uwsgi==2.0.15',
        'ijson==2.3',
        'ujson==1.35'
    ]
)
