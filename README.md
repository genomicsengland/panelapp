PanelApp
========

The Panel App is a crowd-sourced repository of information about various Gene panels.

> This version of the application is under refactoring to be more "cloud-native"

> This documentation page is going to be obsolete and replaced

For building local, dockerised development environment, see [./docker/dev/README.md](docker/dev/README.md)

For notes about cloud-native, AWS porting, see [AWS.md](AWS.md)



Installation
------------

`pip install -e .` will install the application

> If you are using `pipenv` there is a (known problem)[https://github.com/pypa/pipenv/issues/1356] with installing `psycopg2-binary`

> Use `pipenv install --sequential -e .`

## Docker

For development, you can use docker-compose. This will take care of all services and databases locally.

```bash
docker-compose up
docker-compose run web python3 /app/panelapp/manage.py migrate
docker-compose run web python3 /app/panelapp/manage.py collectstatic --noinput
docker-compose run web python3 /app/panelapp/manage.py createsuperuser
```

You can also use docker to deploy the application.

Overview
--------

The Panel App is a project based on Django Framework (v2.1) with PostgreSQL as a backend.

Python version: 3.5

Python dependencies are installed via setup.py.


Development
-----------

```bash
docker-compose up
```

The command above should start all services and Django locally with DEBUG=True so you can use it for the development.

To setup the database schema please run `migrate` command

```bash
docker-compose run web python3 /app/panelapp/manage.py migrate
```

If you need to debug a model use `shell_plus` extension, you can access it via `python manage.py shell_plus`.
This will load all available models and Django settings.

```bash
docker-compose run web python3 /app/panelapp/manage.py shell_plus
```

If you want to access admin panel you can either register on the website, and then change
permissions via `shell_plus` or use `python manage.py createsuperuser` command.

```bash
docker-compose run web python3 /app/panelapp/manage.py createsuperuser
```

We also run Celery with RabbitMQ backend for async tasks. To run celery simply run `celery -A panelapp worker`.
It should start automatically with docker compose.

Gene data

In order to add genes to panels, you need to load gene data. Uncompress `deploy/genes.tgz`,
copy it to `panelapp` folder and run: `docker-compose run web python3 /app/panelapp/manage.py loaddata /app/panelapp/genes.json`.

Genes data contains public gene info, such as ensembl IDs, HGNC symbols, OMIM ID.


Project configuration
---------------------

The project can live in any location on disk, however it requires two writable
locations: one for static files, the other for uploads.

The location for these two directories in configures in `panelapp/settings/<environment>.py` file

Run
`/path/to/ve/bin/python /path/to/app/panelapp/manage.py collectstatic --noinput` for pulling all statics inside the `_staticfiles` folder

Tests
-----

`docker-compose run web pytest`

# Environment Variables

## App Secrets

* `SECRET_KEY` - used to encrypt cookies
* `DATABASE_URL` - PostgreSQL config url in the following format: postgresql://username:password@host:port/database_name
* `CELERY_BROKER_URL` - Celery config for RabbitMQ, in the following format: amqp://username:password@host:port/virtual
* `HEALTH_CHECK_TOKEN` - URL token for authorizing status checks
* `EMAIL_HOST_PASSWORD` - SMTP password
* `ALLOWED_HOSTS` - whitelisted hostnames, if user tries to access website which isn't here Django will throw 500 error
* `DJANGO_ADMIN_URL` - change admin URL to something secure.
* `STATIC_URL` - **TBD**

## Other variables

* `DEFAULT_FROM_EMAIL` - we send emails as this address
* `PANEL_APP_EMAIL` - PanelApp email address
* `DJANGO_LOG_LEVEL` - by default set to INFO, other options: DEBUG, ERROR
* `STATIC_ROOT` - location for static files which are collected with `python manage.py collectstatic --noinput`
* `MEDIA_ROOT` - location for user uploaded files
* `EMAIL_HOST` - SMTP host 
* `EMAIL_HOST_USER` - SMTP username
* `EMAIL_PORT` - SMTP server port
* `EMAIL_USE_TLS` - Set to True (default) if SMTP server uses TLS

Contributing to PanelApp
------------------------

All contributions are under [Apache2 license](http://www.apache.org/licenses/LICENSE-2.0.html#contributions).
