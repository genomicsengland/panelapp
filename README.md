# PanelApp


The Panel App is a crowd-sourced repository of information about various Gene panels.

> The application has been refactored to work on AWS, using AWS services like SQS and S3.
> Using RabbitMQ and local file system is still possible, but backward compatibility is not fully guaranteed.


## Application overview

The Panel App is a project based on Django Framework (v2.1) with PostgreSQL as a backend.

Python version: 3.5

Python dependencies are installed via setup.py.


## Local development environment

We use a dockerised environment for local development, running a Docker Compose cluster including the database and 
[LocalStack](https://github.com/localstack/localstack), mocking AWS SQS and S3 services.

For more details about local development environment and development helpers see [./docker/dev/README.md](docker/dev/README.md).

Note that we use different dockerfiles for local development and deployed environments (see below).

[Docker Compose](docker/dev/docker-compose.yml) and [Makefile](docker/dev/Makefile) are provided to help with the local 
development environment.

LocalStack API is identical to the actual services, but with some remarkable differences in security and URLs.
Beware configurations and security for local development with LocalStack is different from actual AWS services.

It might be handy installing [AWScli-local](https://github.com/localstack/awscli-local) on developer's machine.
A wrapper around AWS cli for interacting with LocalStack (it helps with not `--endpoint-url` and providing dummy 
credentials on every request).

## Cloud environments

All environments, except local development, are supposed to be dockerised, on AWS and using actual AWS services.
We can call them _prod_ environments as they are all identical to Production.

Dockerfiles for _prod_ are different from local-dev ones. They are hardened and optimised to be small (as opposed to 
local-development that includes all dev and test tooling and allows to observe code changes immediately).

The way docker images are scheduled when running on AWS (Kubernetes, ECS...) is irrelevant for the application. 

For details on _prod_ environments see [./docker/prod/README.md](docker/prod/README.md).

> [Docker Compose](docker/prod/docker-compose.yml) and [Makefile](docker/prod/Makefile) in the 
[production docker directory](docker/prod/) are **only for troubleshooting _prod_ docker images**.
They are not supposed to be used in any environments.


## Contributing to PanelApp

All contributions are under [Apache2 license](http://www.apache.org/licenses/LICENSE-2.0.html#contributions).
