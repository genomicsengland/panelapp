# Local development environment

Local development environment (the developer's machine) uses Docker, mounting the application code as volume frm the host machine.

It runs in Docker-compose, including a PostgreSQL instance and [LocalStack](https://github.com/localstack/localstack), for
mocking S3 and SQS.

A [Makefile](./Makefile) is provided for all common operations, including starting and stopping the Docker-compose cluster.

> If you start the docker-compose cluster directly you need to set `TMPDIR` env variable, to `/tmp/localstack` on Linux
> or `/private/tmp/localstack` on OSX.

## Developer machine requirements

* Docker (tested with Docker v.18.09.2 on Mac)
* AWS CLI (tested with aws-cli/1.16.156 Python/2.7.16 botocore/1.12.146)

**Also add an alias `localstack` to `localhost` in your `/etc/hosts` file**.

> This is required because [LocalStack](https://github.com/localstack/localstack), mocking AWS services, is running in
> the Docker-Compose cluster as `localstack` but exposed to the host machine on localhost (port `4572` and `4576` for 
> S3 and SQS, respectively).


## Development lifecycle

All common operations use the [Makefile](./Makefile) in this directory.


### Build dev docker images 

```bash
$ make build
```

### Run and setup the cluster

1. Start a new dev cluster (in detached mode): 
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
5. Deploy static files (takes a while):
    ```bash
    $ make collectstatic
    ```
6. Create admin user (username: `admin`, interactively insert password)
    ```bash
    $ make createsuperuser
    ```

### Developing and accessing the application

The application is accessible from `http://localhost:8080/`

The python code is mounted from the host `<project-root>/panelapp` directory.  Changes to the code are immediately 
reflected into the running containers.

**`setup.py`, `setup.cfg`, `MANIFEST.in` and `VERSION` are copied into the container at docker build-time.**
Any change to these files (e.g. **any changes to a dependency version**) requires rebuilding the container and restarting 
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
* Stop the cluster, without losing the state (db content):
    ```bash
    $ make stop
    ```
    Restart after stopping with `start`.
* Tear down the cluster destroying the state (db content):
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

Django settings: `panelapp.settings.docker-dev`

The [docker-compose.yml](./docker-compose.yml) file set up all required environment variables.

By default mocked S3 and SQS are used. Look at the [docker-dev settings](../../panelapp/panelapp/settings/docker-dev.py)
and [docker-compose.yml](./docker-compose.yml) to make it work with local file-system and RabbitMQ.


## LocalStack

The Docker-Compose cluster also includes an instance of [LocalStack](https://github.com/localstack/localstack) running 
S3, SQS and SES for local development.

The LocalStack UI is accessible from `http://localhost:8090`

Service endpoints are the defaults:

* S3: `http://localhost:4572`
* SQS: `http://localhost:4576`

### LocalStack tmp directory

If you are running Docker Compose directly (or from the IDE) on OSX, beware it requires environment variable
`TMPDIR=/private/tmp/localstack`.

Failing to do this causes LocalStack mounting the host directory `/tmp/localstack` (default on Linux), but Docker has no 
write access to `/tmp` on OSX.
The symptom will be a number of *Mount denied* or permissions errors on starting LocalStack.

### Differences between AWS LocalStack and "the real" AWS thing

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
* Fake-SMTP does not support authentication
