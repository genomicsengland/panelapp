# PanelApp


Panel App is a crowd-sourced repository of information about various gene panels.



## Application overview

Panel App is a project based on Django Framework (v2.1).
It uses PostgreSQL as database, AWS SQS as message queue backend and AWS S3 for file storage.

Python version: 3.5

Python dependencies are installed via `setup.py`.

> The previous version of the application used a hosted RabbitMQ instance and the local file system for file storage.
> This new version has been refactored to work on AWS, leveraging managed AWS services.
> Using RabbitMQ and the local file system is still possible with the Django settings `./panelapp/panelapp/settings/on-prem.py`, 
> but backward compatibility is not fully guaranteed.

All environment are dockerised. 

We make a distinction between local development environments and cloud environments, as they use different Dockerfiles and Django settings.

As much as possible, the application follows the [Twelve-Factors App](https://12factor.net/) design principles.

## Local development environments

**For more details about local development environment setup and tooling, see [./docker/dev/README.md](docker/dev/README.md).**


The local environment allows developers to change the code and observe changes.

It also uses [LocalStack](https://github.com/localstack/localstack), to mock AWS SQS and S3 services.

A [Docker Compose](docker/dev/docker-compose.yml) stack that includes PanelApp (_Web_ and _Worker_), a PostgreSQL instance and [LocalStack](https://github.com/localstack/localstack) is provided.

_Web_ and _Worker_ components share the same codebase but _web_ runs as web-app server while _worker_ runs as Celery.

A [Makefile](docker/dev/Makefile) is provided to facilitate dev-time operations.


## Cloud environments

**For details on _Cloud_ environments see [./docker/cloud/README.md](docker/cloud/README.md).**

All environments, except the local-dev environment, are assumed to run on AWS against actual AWS services.

Dockerfiles for cloud are optimised for security and size.

The application is agnostic to the container scheduler platform it runs in (e.g. Kubernetes, ECS).

Docker-compose and Makefile in  [./docker/cloud/](docker/cloud/) are for locally troubleshooting production docker images.
They are NOT supposed to be used to deploy the application in any environment.

## Contributing to PanelApp

All contributions are under [Apache2 license](http://www.apache.org/licenses/LICENSE-2.0.html#contributions).
