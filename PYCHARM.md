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
	*   `Preferences` : `Project: application` > `Project interpreter` > 
		*   Add : `Docker Compose`
			*   Server: `Docker`
			*   Configuration files: `./docker/dev/docker-compose.yml`
			*   Service: `web` 
			*   Evironment Variables: `TMPDIR=/private/tmp/localstack`
		*   Path Mappings: `<project-root>`->`/app`
3. Enable Django support:
	*  `Preferences` : `Language & Frameworks` > `Django` : enable
		* Django Project Root: `<python-project-root>/panelapp`
		* Settings: `panelapp/settings/docker-dev.py`
		* Manage Script: `manage.py`
4. Set up project source directory:
	*  `Preferences` : `Project: application` > `Project Structure`
		* Add `./panelapp` to Sources
5. Docker-compose cluster Run Profile (not mandatory but handy):
	* `Run` > `Edit Configurations`: Add `Docker > Docker-compose`
		*  Compose file: `./docker/dev/docker-compose.yml`
		*  Environment Variables: `TMPDIR=/private/tmp/localstack`
6. Django app Run profile:
	* `Run` > `Edit Configurations`: Add `Django server`
		* Host: `0.0.0.0`, Port: `8080`
		* Python Interpreter: `Remote Python 3.6.8 Docker Compose...` (the one created above)