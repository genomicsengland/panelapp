"""TODO: module doc..."""

import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

from panelapp.panelapp import get_package_version


setup(
    name='panelapp',
    version=get_package_version(),
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
        'pytest==3.6.1',
        'pytest-django==3.2.1',
        'flake8==3.5.0',
        'faker==0.8.15',
        'factory_boy==2.11.1',
        'pytest-cov==2.5.1'
    ],
    dev_requires=[
        'django-debug-toolbar==1.9.1',
        'django-extensions==2.0.7',
        'ipython==6.4.0'
    ],
    install_requires=[
        'django==2.0.6',
        'simplejson==3.8.2',
        'psycopg2-binary==2.7.4',
        'dj-database-url==0.5.0',
        'django-model-utils==3.1.2',
        'djangoajax==3.0.2',
        'djangorestframework==3.8.2',
        'django-tables2==1.21.2',
        'django-filter==1.1.0',
        'django-cors-headers==2.1.0',
        'django-autocomplete-light==3.2.10',
        'django-markdown-deux==1.0.5',
        'django-bootstrap3==10.0.1',
        'django-markdownx==2.0.23',
        'Markdown==2.6.11',
        'django-object-actions==0.10.0',
        'django-mathfilters==0.4.0',
        'celery==4.2.0',
        'more-itertools==4.2.0',
        'requests==2.19.1',
        'uwsgi==2.0.15',
        'ijson==2.3',
        'ujson==1.35',
        'django-admin-list-filter-dropdown==1.0.1',
        'pytz==2018.4',
        'gunicorn==19.9.0',
    ]
)
