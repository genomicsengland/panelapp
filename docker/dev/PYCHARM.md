# Notes about setting up PyCharm (Pro)

This document is about using PyCharm Professional with Docker Compose.

Even though almost everything also applies to Linux, it is specific to OSX with Docker for Mac.

All settings not explicitly mentioned should be left as by default.


## Requirements

* PyCharm Professional 2019.1+
* Docker 18.09.2+

## Initial PyCharm setup

1. Create *Docker* execution server:
	* `Preferences` : `Build, Execution, Deployment` > `Docker` + `Docker for Mac`
2. Set up *Python Interpreter* = *Docker Compose*
	*   `Preferences` : `Project: panelapp` > `Project interpreter` > 
		*   Add : `Docker Compose`
			*   Server: `Docker`
			*   Configuration files: `./docker/dev/docker-compose.yml`
			*   Service: `web` 
			*   Environment Variables: `TMPDIR=/private/tmp/localstack`
		*   Path Mappings: `<project-root>`->`/app`
3. Enable Django support:
	*  `Preferences` : `Language & Frameworks` > `Django` : enable
		* Django Project Root: `<python-project-root>/panelapp`
		* Settings: `panelapp/settings/docker-dev.py`
		* Manage Script: `manage.py`
4. Set up project source directory:
	*  `Preferences` : `Project: panelapp` > `Project Structure`
		* Add `./panelapp` to Sources
5. Docker-compose cluster Run Profile (not mandatory but handy):
	* `Run` > `Edit Configurations`: Add `Docker > Docker-compose`
		*  Compose file: `./docker/dev/docker-compose.yml`
		*  Environment Variables: `TMPDIR=/private/tmp/localstack`
6. Django app Run profile:
	* `Run` > `Edit Configurations`: Add `Django server`
		* Host: `0.0.0.0`, Port: `8000` (Django server listens to 8000 that is mapped to 8080 on localhost)
		* Python Interpreter: `Remote Python 3.6.8 Docker Compose...` (the one created above)
		
		
## Preparing the dev environment

Run Django commands from the IDE:

1. `Tools` > `Run manage.py Tasks`:
    * `migrate`
    * `loaddata /app/genes.json`
2. Create mock AWS resources in LocalStack (you must use the `Makefile` in `./docker/dev` at the moment)
    * From `./docker/dev` run `make mock-aws`
3. `Tools` > `Run manage.py Tasks`:
    * `collectstatic --noinput`
    * `createsuperuser` (create admin user credentials) 

    
Now you may run the Django application using the Run profile and access it from `http://127.0.0.1:8080`

## Remote debugging

There is a [known issue](https://youtrack.jetbrains.com/issue/PY-32022) preventing from debugging an application
running inside Docker if the Dockerfile defines a custom `ENTRYPOINT`
