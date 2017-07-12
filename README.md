PanelApp
========

The Panel App is a crowd-sourced repository of information about various Gene panels.


Installation (vagrant route)
----------------------------

If you have vagrant installed run `vagrant up` this should provision the server with all dependencies.

Use `vagrant ssh ` to login into the box.


## Install Vagrant

To use Vagrant you'd need to install [VirtualBox](https://www.virtualbox.org/wiki/Downloads) and [Vagrant](https://www.vagrantup.com/downloads.html)


Overview
--------

The Panel App is a project based on Django Framework (v1.11) with PostgreSQL as a backend.

Python version: 3.5 (installed via apt-get on Ubuntu 16.04.2)

Python dependencies are installed via requirements file which is located in deploy folder.


Development
-----------

After you've logged into vagrant box with `vagrant ssh` the virtualenv should be activated and you should cd to the project folder automatically. Your local file system of the project is linked to `/srv/panelappv2`

Run `python manage.py runserver_plus` it will run the local version.

If you need to debug a model use `shell_plus` extension, you can access it via `python manage.py shell_plus` - it will load all available models and Django settings.

If you want to access admin panel you can either register on the website, and then change
permissions via `shell_plus` or use `python manage.py createsuperuser` command.

We also run Celery with RabbitMQ backend for async tasks. To run celery simply run `celery -A panelapp worker`


Project configuration
---------------------

The project can live in any location on disk, however it requires two writable
locations: one for static files, the other for uploads.

The location for these two directories in configures in `panelapp/settings/<environment>.py` file

Run
`/path/to/ve/bin/python /path/to/app/panelapp/manage.py collectstatic --noinput` for pulling all statics inside the `_staticfiles` folder

Tests
-----

To run unit tests SSH into Vagrant instance and run `pytest`. It does take some time.


Migration notes
---------------

- [x] Script to migrate users
- [x] Script to migrate images
- [x] Script to migrate HomeText
  - [x] Replace HomeText images urls from `/static/uploads/` to `/media/`
  - [ ] nginx 301 redirects for images `/static/uploads/` to `/media/`
- [ ] Django redirects for panels
- [ ] We need to copy upload files and images


# Redirects

We can actually leave /static/uploads/ and use uWSGi to point to the new location which will be the same folder where /media/ endpoint requests files from.

For example `--static-map /static/uploads=/opt/panelapp/_mediafiles`

# Environment Variables

## App Secrets

* `SECRET_KEY` - used to encrypt cookies
* `DATABASE_URL` - PostgreSQL config url in the following format: postgresql://username:password@host:port/database_name
* `CELERY_BROKER_URL` - Celery config for RabbitMQ, in the following format: amqp://username:password@host:port/virtual
* `HEALTH_CHECK_TOKEN` - URL token for authorizing status checks
* `EMAIL_HOST_PASSWORD` - SMTP password

## Other variables

* `DEFAULT_FROM_EMAIL` - we send emails as this address
* `PANEL_APP_EMAIL` - PanelApp email address
* `DJANGO_LOG_LEVEL` - by default set to INFO, other options: DEBUG, ERROR
* `STATIC_ROOT` - location for static files which are collected with `python manage.py collectstatic --noinput`
* `MEDIA_ROOT` - location for user uploaded files
* `CELL_BASE_CONNECTOR_REST` - Cell Base API endpoint, by default it's http://bioinfo.hpc.cam.ac.uk/cellbase/webservices/rest/
* `EMAIL_HOST` - SMTP host 
* `EMAIL_HOST_USER` - SMTP username
* `EMAIL_PORT` - SMTP server port
* `EMAIL_USE_TLS` - Set to True (default) if SMTP server uses TLS


# V1 to V2 data migration

If you have a local panelappv1 running you can checkout branch `feat/v2export` and run `python manage.py v2export` - this will create a new directory with the JSON files.

To import the data simply copy `v1dump_...` folder to your Vagrant synced folder and run `python manage.py v2import <full path to the new folder>`. The import will take some time depending on how much data you have.
