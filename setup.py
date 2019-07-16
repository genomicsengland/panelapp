"""TODO: module doc..."""

import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_path, "./VERSION"), "r") as version_file:
    version = str(version_file.readline()).strip()


setup(
    name="panelapp",
    version=version,
    author="Antonio Rueda-Martin,Oleg Gerasimenko",
    author_email="antonio.rueda-martin@genomicsengland.co.uk,oleg.gerasimenko@genomicsengland.co.uk",
    url="https://github.com/genomicsengland/PanelApp2",
    description="PanelApp",
    license="Internal GEL use only",  # example license
    classifiers=[
        "Environment :: Other Environment",
        "Intended Audience :: Other Audience",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.5",
        "Topic :: Scientific/Engineering",
    ],
    packages=["panelapp"],
    include_package_data=True,
    setup_requires=["pytest-runner"],
    extras_require={
        "dev": ["django-debug-toolbar==1.11", "ipython==6.4.0", "Werkzeug==0.14.1"],
        "tests": [
            "pytest==3.7.1",
            "pytest-django==3.3.3",
            "flake8==3.5.0",
            "faker==0.8.15",
            "factory_boy==2.11.1",
            "pytest-cov==2.5.1",
        ],
    },
    install_requires=[
        "django==2.1.10",
        "simplejson==3.16.0",
        "PyYAML==5.1",
        "psycopg2-binary==2.7.4",
        "dj-database-url==0.5.0",
        "django-model-utils==3.1.2",
        "djangoajax==3.0.2",
        "djangorestframework==3.9.4",
        "django-extensions==2.1.0",
        "django-tables2==1.21.2",
        "django-cors-headers==2.1.0",
        "django-autocomplete-light==3.3.0",
        "django-markdown-deux==1.0.5",
        "django-bootstrap3==10.0.1",
        "django-markdownx==2.0.23",
        "Markdown==2.6.11",
        "django-object-actions==0.10.0",
        "django-mathfilters==0.4.0",
        "celery==4.2.1",
        "more-itertools==4.2.0",
        "requests==2.22.0",
        "uwsgi==2.0.15",
        "django-admin-list-filter-dropdown==1.0.1",
        "pytz==2018.4",
        "gunicorn==19.9.0",
        "django-array-field-select==0.2.0",
        "drf-yasg==1.15.0",
        "flex==6.14.0",
        "swagger-spec-validator==2.4.3",
        "djangorestframework-jsonapi==2.7.0",
        "drf-nested-routers==0.90.2",
        "django-array-field-select==0.2.0",
        "django-qurl-templatetag==0.0.13",
        "django-click==2.1.0",
        "django-filter==2.0.0",
        "django-storages==1.7.1",
        "boto3==1.9.147",
        "pycurl==7.43.0.2",
        "simple-json-log-formatter==0.5.5",
    ],
)
