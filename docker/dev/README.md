# Local development environments

Local-dev uses Docker and the [Docker Compose stack](./docker-compose.yml) included.

Please use the [Makefile](./Makefile) provided to set up the local dev environment.

## Docker-Compose stack
 
Docker Compose stack includes:

* _Web_ component: a Django app server run with `runserver_plus`.
* _Worker_  component: a Celery application.
* A PostgreSQL instance
* [LocalStack](https://github.com/localstack/localstack), mocking S3 and SQS.
 
The application source code fis mounted from the local machine as volumes into the running containers.
Any change to the code will be immediately reflected.

> If you start the docker-compose cluster directly, without the Makefile, you need to set `TMPDIR` env variable. 
> To `/tmp/localstack` on Linux or `/private/tmp/localstack` on OSX.

## Developer machine requirements

Software requirements:

* Docker: tested with Docker v.18.09.2 on Mac
* AWS CLI: tested with aws-cli/1.16.156 Python/2.7.16 botocore/1.12.146

Local setup requirements:

* Edit your `/etc/hosts` file adding `localstack` as alias to `localhost`

This is required because [LocalStack](https://github.com/localstack/localstack), mocking AWS services, is running in
the Docker-Compose cluster as `localstack` but exposed to the host machine on localhost (port `4572` and `4576` for 
S3 and SQS, respectively).

## Dockerfiles

_Web_ and _Worker_ have separate Dockerfiles: [`Dockerfile-web`](./Dockerfile-web) and [`Dockerfile-worker`](./Dockerfile-worker).

All Python dependencies, including dev and test deps, are installed as editable.

## Development lifecycle

You should use the [Makefile](./Makefile) in this directory for all common tasks.


### Build dev docker images 

```bash
$ make build
```

> You must rebuild the base docker images if you change any dependencies in `setup.py`. 
> Any other code change does not require to rebuild, as the source code is mounted from the host machine file system
> and installed in editable mode.

### Run and setup the stack

To start an empty application from scratch (no Panel, but includes Genes data).

1. Start a new dev stack (in detached mode): 
    ```bash
    $ make up
    ```
2. Create db schema or apply migration (give few seconds to the db container to start, before running `migrate`): 
    ```bash
    $ make migrate
    ```
3. Load gene data: 
    ```bash
    $ make loaddata
    ```
    Genes data contains public gene info, such as ensemble IDs, HGNC symbols, OMIM ID.
4. Create all required mock AWS resources, if the do not exist:
    ```bash
    $ make mock-aws
    ```
5. Deploy static files:
    ```bash
    $ make collectstatic
    ```
6. Create admin user
    ```bash
    $ make createsuperuser
    ```
    This is the user to log into the webapp: username=`admin`, pwd=`changeme`, email=`admin@local`


### Developing and accessing the application

The application is available at `http://localhost:8080/`

The Python code is mounted from the host `<project-root>/panelapp` directory.  

**`setup.py`, `setup.cfg`, `MANIFEST.in` and `VERSION` are copied into the container when the Docker image is build.**
Any change to these files (e.g. **changes to dependencies versions**) requires rebuilding the container and restarting 
the cluster.

* Run tests:
    ```bash
    $ make tests
    ```
* To tail logs from **all** containers:
    ```bash
    $ make logs
    ```
    To see logs from a single service you must use `docker-compose` or `docker` commands, directly.
* Stop the stack, without losing the state (db content):
    ```bash
    $ make stop
    ```
    Restart after stopping with `start`.
* Tear down the stack destroying the state (db content):
    ```bash
    $ make down
    ```
* The content of mock S3 buckets is actually saved in the temp directory (`/tmp/localstack` on Linux or 
    `/private/tmp/localstack` on OSX). When you re-create the cluster and `mock-aws` resources, content of S3 buckets will 
    be there. To clear them use:
    ```bash
    $ make clear-s3
    ```
* Run a Django arbitrary command:
    ```bash
    $ make command <command> [<args>...]
    ```
    E.g. to run shell_plus extension to debug models
    ```bash
    $ make command shell_plus

    ```

## Application Configuration

Django settings: [`panelapp.settings.docker-dev`](../../panelapp/panelapp/settings/docker-dev.py).

The [docker-compose.yml](./docker-compose.yml) sets all required environment variables.

By default, it uses mocked S3 and SQS by LocalStack.

> You could run the application against RabbitMQ and the local file system, tweaking 
> [docker-dev settings](../../panelapp/panelapp/settings/docker-dev.py) and [docker-compose.yml](./docker-compose.yml),
> but this backward compatibility may be dropped in the future.

Sending email is completely disabled: it only outputs to console.

## LocalStack

The Docker-Compose cluster also includes an instance of [LocalStack](https://github.com/localstack/localstack) running 
S3, SQS for local development.

A minimal LocalStack UI is accessible from `http://localhost:8090/`

Service endpoints are LocalStack defaults:

* S3: `http://localhost:4572`
* SQS: `http://localhost:4576`


> If you are running Docker Compose directly (or from the IDE) on OSX, beware that requires the environment variable
> `TMPDIR=/private/tmp/localstack`. Failing to do this causes LocalStack mounting the host directory `/tmp/localstack` 
> (default on Linux), but Docker has no write access to `/tmp` on OSX. The symptom will be a number of *Mount denied* 
> or permissions errors on starting LocalStack.

### Differences between AWS LocalStack and real AWS services

* Running containers do not have any IAM Role; AWS credentials are not actually required but all libraries/cli tools 
    expect them. `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` must be set as environment variables in the running
    container (actual values do not matter).
* [Service endpoints](https://github.com/localstack/localstack#user-content-overview) are different. 
    You have to pass `endpoint_url` to most of libraries/CLI commands. Also, you may have to disable `https` with
    `use_ssl=False` as LocalStack uses http while S3, for example, uses https by default.
* Containers running inside the docker-compose cluster see all LocalStack service coming from `localstack` host. From the
    host machine they are actually exposed to `localhost`. To make scripts running both inside the containers and from
    the host machine, set an alias `localstack` alias to `localhost` in the host machine's `/etc/hosts` file
* LocalStack SES does not support SMTP

### AWScli-local

It might be handy installing [AWScli-local](https://github.com/localstack/awscli-local) on developer's machine.

It is a wrapper around AWS cli for interacting with LocalStack (it helps with not `--endpoint-url` and providing dummy 
credentials on every request).

## Known Issues

Using different dockerfiles for local development and production is actually violating 
[12-Factor App Dev-Prod parity](https://12factor.net/dev-prod-parity).

The main goal was to have a proper production docker image: no dev/test dependency, lightweight base image, dependencies not 
installed as "editable"...
 
A common pattern is building dev and test images on top of the production image. Unfortunately, this cannot be easily done
in Python installing dependencies with setup.py, without loosening the production image.

There is space for improvement here.
