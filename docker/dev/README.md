# Local development with Docker-compose

> DOCUMENT TO BE IMPROVED

This directory contains Docker and Docker-compose files to be used for local development.

You are supposed to use `make` rather than calling `docker-compose` directly.

This is tested with Docker v.18.09.2

All commands are supposed to be run from this directory.

### Build dev docker images 
```bash
$ make build
```

### Run and setup the cluster

As separate steps:

1. Start a new dev cluster (in detached mode): 
    ```bash
    $ make run
    ```
2. Create db schema or apply migration: 
    ```bash
    $ make migrate
    ```
3. Load genes data: 
    ```bash
    $ make loaddata
    ```
4. Deploy static files (takes a while):
    ```bash
    $ make collectstatic
    ```
 
Alternatively, as single step: 

```bash
$ make setup
```

### Developing and accessing the application

The application is accessible from `http://localhost:8090/`

The python code is mounted from the host `./panelapp` directory. 
Changes to the code are immediately reflected into the running containers.

`setup.py`, `setup.cfg`, `MANIFEST.in` and `VERSION` are copied into the container at build-time.
Any change to these files requires rebuilding the container and restarting the cluster.


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
