# PanelApp


The Panel App is a crowd-sourced repository of information about various Gene panels.



## Application overview

The Panel App is a project based on Django Framework (v2.1).
It uses PostgreSQL as relational database, AWS SQS as message queue backend and AWS S3 for file storage..

Python version: 3.5

Python dependencies are installed via setup.py.

> The previous version of the application was using a hosted RabbitMQ middleware and local file system for file storage.
> This new version has been refactored to work on AWS, leveraging managed AWS services.
> Using RabbitMQ and local file system is still possible, using the Django settings `./panelapp/panelapp/settings/on-prem.py`, 
> but backward compatibility is not fully guaranteed.

All environment are dockerised. 
We make a distinction between "Local Development" environment and "Cloud environments", as the use different Dockerfiles
and Django settings.

## Local development environment

The local environment allows developers to change the code and immediately observe the changes.

It also uses [LocalStack](https://github.com/localstack/localstack), to mock AWS SQS and S3 services.

A Docker compose cluster includes the two runtime PanelApp component, _web_ and _worker_, a PostgreSQL instance,
[LocalStack](https://github.com/localstack/localstack), to mock AWS SQS and S3 services.

_Web_ and _Worker_ components share the same codebase but _web_ runs as web-app server while _worker_ runs as Celery.

For more details about local development environment setup and tooling, see [./docker/dev/README.md](docker/dev/README.md).

[Docker Compose](docker/dev/docker-compose.yml) and [Makefile](docker/dev/Makefile) help with normal dev-time operations.


## Cloud environments

All environments, except local development, run on AWS and using actual AWS services.
They are all identical to the actual Production, so we call them _prod_ environments.

Dockerfiles for _prod_ are hardened and optimised to be small.

The way docker images are scheduled (Kubernetes, ECS...) is irrelevant for the application.

For details on _prod_ environments see [./docker/prod/README.md](docker/prod/README.md).

> [Docker Compose](docker/prod/docker-compose.yml) and [Makefile](docker/prod/Makefile) in the 
[production docker directory](docker/prod/) are **for troubleshooting _prod_ docker images**.
They are not supposed to be used in any real environment.


## Contributing to PanelApp

All contributions are under [Apache2 license](http://www.apache.org/licenses/LICENSE-2.0.html#contributions).
