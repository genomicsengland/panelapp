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

- [] FIXME this should be done automatically with settings file selecting the folder if environment variable isn't set.

Run
`/path/to/ve/bin/python /path/to/app/panelapp/manage.py collectstatic --noinput` for pulling all statics inside the `_staticfiles` folder


nginx configuration
--------------------

Create a normal file in `/etc/nginx/site-available/` directory called
`panelapp.conf` and make the contents:

```
# TODO
```


TODO
----

- [ ] Add nginx config
- [ ] Add supervisor config
- [ ] Add notes on how to run tests and coverage
- [ ] Add Ansible scripts for setting up local, staging, and production environments
- [ ] Add flake8


Migration notes
---------------

- [ ] Script to migrate users
- [ ] Script to migrate images
- [ ] Script to migrate HomeText
  - [ ] Replace HomeText images urls from `/static/uploads/` to `/media/`
  - [ ] nginx 301 redirects for images `/static/uploads/` to `/media/`
- [ ] nginx 301 redirects for panels
- [ ] nginx 301 redirects for genes
