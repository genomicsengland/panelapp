# Cloud environments

This directory contains Dockerfiles for AWS environments.

All cloud environments are intended to be as identical as possible, using thesame Docker images and Django settings, except for environment-specific parameters.

## Dockerfiles

The cloud docker images are designed to run on AWS, using S3 and SQS, and run within any container scheduler platform, Kubernetes, ECS, ECS/Fargate... (Docker Compose is not intended for production use).

* [Base image Dockerfile](./Dockerfile-base)
* [Web Dockerfile](./Dockerfile-web), starts the Django application with Gunicorn
* [Worker Dockerfile](./Dockerfile-worker), starts Celery

> Docker Compose](./docker-compose.yml) and [Makefile](./Makefile) in this directory are **for troubleshooting docker 
> images** only. They are not supposed to be used in any environments.

## Application configuration

The Django settings module for these environments is 
[`panelapp.settings.docker-aws`](../../panelapp/panelapp/settings/docker-aws.py).

The same Django settings module is used for all environments.
All environment-specific parameters are passed as environment variables (not by switching Django setting module).
 
###  Mandatory environment variables

All of the following environment variables must be set:

#### Non-Secrets

* `AWS_S3_STATICFILES_BUCKET_NAME` - Name of the S3 bucket for storing static files
* `AWS_S3_MEDIAFILES_BUCKET_NAME` - Name of the S3 bucket for storing media (uploaded) files
* `AWS_REGION` - AWS Region
* `AWS_S3_STATICFILES_CUSTOM_DOMAIN` - Custom CDN domain to serve static files from (e.g. `cdn.mydomain.com` - no trailing `/`)
* `AWS_S3_MEDIAFILES_CUSTOM_DOMAIN` - Custom CDN domain to serve media files from (e.g. `cdn.mydomain.com` - no trailing `/`)
* `ALLOWED_HOSTS` - whitelisted hostnames, if user tries to access website which isn't here Django will throw 500 error
* `DEFAULT_FROM_EMAIL` - we send emails as this address
* `PANEL_APP_EMAIL` - PanelApp email address
* `EMAIL_HOST` - SMTP server hostname
* `EMAIL_PORT` - SMTP server port
* `PANEL_APP_BASE_URL` - Public URL of the web application

#### Secrets

* `DATABASE_HOST` - PostgreSQL hostname
* `DATABASE_PORT` - (default: 5432) PostgreSQL port
* `DATABASE_NAME` - (default: "panelapp") db name
* `DATABASE_USER` - PostgreSQL username
* `DATABASE_PASSWORD` - PostgreSQL password
* `EMAIL_HOST_USER` - SMTP username (no SMTP authentication if omitted)
* `EMAIL_HOST_PASSWORD` - SMTP password (no SMTP authentication if omitted)
* `SECRET_KEY` - Secret for encrypting cookies


### Optional environment variables

#### Non-secrets

* `DJANGO_LOG_LEVEL` - to override Django log-level (default=`INFO`). This also controls Gunicorn and Celery log level.
* `EMAIL_USE_TLS` - Set to `False` to prevent SMTP from using TLS
* `SQS_QUEUE_VISIBILITY_TIMEOUT` - SQS topic _Visibility Timeout_. Must be identical to the Visibility Timeout of the SQS queue
* `TASK_QUEUE_NAME` - Name of the SQS queue (default: `panelapp`)     
* `AWS_STATICFILES_LOCATION` - specify it to change the path static files are located within their S3 bucket (default: `static`)
* `AWS_MEDIAFILES_LOCATION` - specify it to change the path media files are located within their S3 bucket (default: `media`)

#### Secrets

* `DATABASE_URL` - (**alternative to passing separate `DATABASE_*` parameters**)
    database config URL, in the format: `postgresql://{username}:{password}@{host}:{port}/{database_name}`
* `DJANGO_ADMIN_URL` - change admin URL to something more secure (by obscurity) than the default `/admin`
* `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` - required if not using IAM Roles to authenticate access to S3 buckets   
* `CELERY_BROKER_URL` - Only required if not using IAM Roles for SQS authentication. 
    It must be in the format `sqs://{aws_access_key}:{aws_secret_key}@`.

### Gunicorn settings (_Web_ image only)

All [Gunicorn settings](http://docs.gunicorn.org/en/latest/settings.html) may be overridden by an environment variable 
named `GUNICORN_<UPPERCASE-SETTING-NAME>` (e.g. `GUNICORN_WORKERS` overrides `workers`) 

Defaults:

* `GUNICORN_WORKERS` (`workers`): 8 
* `GUNICORN_TIMEOUT` (`timeout`, in seconds): 300

# AWS resources

_Web_ and _Worker_ are completely stateless. 
They may scale out for HA as required.

## S3 buckets

Two S3 buckets are used for storing files:

1. Media (uploaded) files
2. Static files (images, css, js...)

The _Media_ bucket must be accessible for read+write by both _Web_ and _Worker_.

The _Static_ bucket must be accessible for read+write by _Web_ only 

The _Static_ bucket must also be publicly accessible, either directly (not-recommended) or through CloudFront CDN 
(recommended).

`AWS_S3_STATICFILES_CUSTOM_DOMAIN` defines the public DNS domain to access the _Static_ bucket (e.g. the CloudFront domain).

> By default, static files are stored in a `/static` "subdirectory" of the bucket and are expected to be served from 
`https://<AWS_S3_STATICFILES_CUSTOM_DOMAIN>/static/` base URL.

## SQS queue

The application uses an SQS queue named `panelapp` to schedule jobs picked up by _Worker_.

It is recommended to create the SQS queue beforehand.
Infrastructure should be managed securely outside of the running application.
You should not give the application permissions to create queues at runtime.

The queue **_Visibility Timeout_ must be `360` (seconds)**. 
If you use a different value, do not forget to override `SQS_QUEUE_VISIBILITY_TIMEOUT` to match the queue timeout.

> If the _Visibility Timeout_ does not match what the application is expecting, Celery will try to create a new queue.

## Database

The application expects a PostgreSQL-compatible DB.

The application has been tested with AWS Aurora, but PostgreSQL RDS should also work.

## AWS resource security 

Authentication with the database uses username and password (part of `DATABASE_URL`).

Access SQS and S3 should be authorised using IAM Policy.

No `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` must be explicitly passed to the application (this is not secure!)

### Policy for SQS access

This should be the Least-Privilege IAM Policy to access the SQS Queue.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:DeleteMessage",
                "sqs:GetQueueUrl",
                "sqs:ChangeMessageVisibility",
                "sqs:DeleteMessageBatch",
                "sqs:SendMessageBatch",
                "sqs:ReceiveMessage",
                "sqs:SendMessage",
                "sqs:GetQueueAttributes",
                "sqs:ChangeMessageVisibilityBatch"
            ],
            "Resource": "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:<QUEUE_NAME>"
        },
        {
            "Effect": "Allow",
            "Action": "sqs:ListQueues",
            "Resource": "*"
        }
    ]
}
```

Note the default queue name is `panelapp`, unless overridden.

### Policy to allow the application to access Media and Static S3 buckets

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Sid": "Stmt1559654322774",
          "Action": [
            "s3:DeleteObject",
            "s3:PutObjectAcl",
            "s3:GetObjectAcl",
            "s3:GetObject",
            "s3:HeadBucket",
            "s3:ListBucket",
            "s3:PutObject"
          ],
          "Effect": "Allow",
          "Resource": [
            "arn:aws:s3:::<STATIC-BUCKET-NAME>/*",
            "arn:aws:s3:::<MEDIA-BUCKET-NAME>/*"
            ]
        }
    ]
}
```


## Logging

All application components logs to stdout in JSON, using `python3-json-log-formatter==1.6.1` as log formatter, for 
easier log aggregation and indexing.

Logging level is controlled by `DJANGO_LOG_LEVEL` (default = `INFO`). Note that this does not only control Django, but also
Celery and Gunicorn logging.
