# Local development with Docker-compose

> DOCUMENT TO BE IMPROVED

This directory contains Docker and Docker-compose files to be used for local development.

You are supposed to use `make` rather than calling `docker-compose` directly.

All commands are supposed to be run from this directory.

### Requirements

This is tested with Docker v.18.09.2

It requires `aws` CLI installed.


#### Edit `hosts` file

To develop locally against AWS LocalStack, your machine has to resolve `localstack` hostname as localhost.

Edit `/etc/hosts` and add `localstack` as alias to `localhost`.

### Build dev docker images 

```bash
$ make build
```

### Run and setup the cluster

As separate steps:

1. Start a new dev cluster (in detached mode): 
    ```bash
    $ make up
    ```
2. Create db schema or apply migration (give time to the db container to start, before running `migrate`. 
Possibly, have a look at logs with `make logs` to see it starting): 
    ```bash
    $ make migrate
    ```
3. Load genes data: 
    ```bash
    $ make loaddata
    ```
4. Create all required mock, local AWS resources (a bit dumb at the moment: it explodes if any resources already exists):
    ```bash
    $ make mock-aws
    ```
5. Deploy static files (takes a while):
    ```bash
    $ make collectstatic
    ```
6. Create admin user (username: `admin`, interactively insert passwod)
    ```bash
    $ make createsuperuser
    ```

### Developing and accessing the application

The application is accessible from `http://localhost:8080/`

The python code is mounted from the host `./panelapp` directory. 
Changes to the code are immediately reflected into the running containers.

`setup.py`, `setup.cfg`, `MANIFEST.in` and `VERSION` are copied into the container at build-time.
Any change to these files (e.g. **any changes to a dependency version**) requires rebuilding the container and restarting 
the cluster.


To run tests:

```bash
$ make tests
```

To tail logs from all containers:

```bash
$ make logs
```



### Stop, restart and destroy the cluster

Stop the cluster, without losing the state: 

```bash
$ make stop
```

Restart a stopped cluster: 
    
```bash
$ make start
```

Destroy the cluster, including the state: 
    ```bash
    $ make down
    ```

### Run any Django command

To run a generic command through `manage.py`:

```bash
$ make command <command>
```

Useful commands:

* `createsuperuser`: create a superuser to access admin panel
* `shell_plus`: run shell_plus extension to debug models

## LocalStack

The Docker-Compose cluster also includes an instance of [LocalStack](https://github.com/localstack/localstack) running 
S3, SQS and SES for local development.

The LocalStack UI is accessible from `http://localhost:8090`

Service endpoints are the defaults:

* S3: `http://localhost:4572`
* SQS: `http://localhost:4576`
* SES `http://localhost:4579`

### LocalStack tmp directory

If you are running Docker Compose directly (or from the IDE) on OSX, beware it requires environment variable
`TMPDIR=/private/tmp/localstack`.

Failing to do this causes LocalStack mounting the host directory `/tmp/localstack` (default on Linux), but Docker has no 
write access to `/tmp` on OSX.
The symptom will be a number of *Mount denied* or permissions errors on starting LocalStack.
