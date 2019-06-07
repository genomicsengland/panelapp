# Production docker

This directory contains Dockerfiles for AWS environments (as opposed to local development).

All AWS environment are identical to Production. Environment-specific configurations are passed to the runtime container
as environment variables.

The production docker images is designed to run on AWS, using S3 and SQS (as opposed to file-system storage and RabbitMQ), scheduler by any
container scheduler, Kubernetes, ECS, ECS/Fargate... (Docker-Compose is not a production scheduler).

> Docker Compose](./docker-compose.yml) and [Makefile](./Makefile) in this directory are **for troubleshooting docker 
> images** only. They are not supposed to be used in any environments.

The Django settings module for these environments is `panelapp.settings.docker-aws`.

> The same settings is used for all environments. All settings changing with Staging... Prod etc are passed as environment 
> variables. Not switching Django setting module.
 
##  Mandatory environment variables

All of the following environment variables must be set:

### Non-Secrets

* `AWS_S3_STATICFILES_BUCKET_NAME` - Name of the S3 bucket for storing static files
* `AWS_S3_MEDIAFILES_BUCKET_NAME` - Name of the S3 bucket for storing media (uploaded) files
* `AWS_REGION` - AWS Region
* `AWS_S3_STATICFILES_CUSTOM_DOMAIN` - Custom CDN domain to serve static files from (e.g. `cdn.mydomain.com` - no trailing `/`)
* `ALLOWED_HOSTS` - whitelisted hostnames, if user tries to access website which isn't here Django will throw 500 error
* `DEFAULT_FROM_EMAIL` - we send emails as this address
* `PANEL_APP_EMAIL` - PanelApp email address
* `EMAIL_HOST` - SMTP server hostname
* `EMAIL_PORT` - SMTP server port

### Secrets

* `DATABASE_URL` - PostgreSQL config url, in the format: `postgresql://{username}:{password}@{host}:{port}/{database_name}`
* `EMAIL_HOST_USER` - SMTP username (no SMTP authentication if omitted)
* `EMAIL_HOST_PASSWORD` - SMTP password (no SMTP authentication if omitted)
* `HEALTH_CHECK_TOKEN` - Token to authenticate health check endpoint requests
* `SECRET_KEY` - Secret for encrypting cookies


## Optional environment variables

### Non-secrets

* `DJANGO_LOG_LEVEL` - to override Django log-level (default=`INFO`). This also controls Gunicorn and Celery log level.
* `EMAIL_USE_TLS` - Set to `False` to prevent SMTP from using TLS
* `SQS_QUEUE_VISIBILITY_TIMEOUT` - SQS topic _Visibility Timeout_. Must be identical to the Visibility Timeout of the SQS queue
* `TASK_QUEUE_NAME` - Name of the SQS queue (default: `panelapp`)     
* `AWS_STATICFILES_LOCATION` - specify it to change the path static files are located within their S3 bucket (default: `static`)
* `AWS_MEDIAFILES_LOCATION` - specify it to change the path media (uploaded) files are located within their S3 bucket 
    (default: `uploads`)

### Secrets

* `DJANGO_ADMIN_URL` - change admin URL to something secure
* `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` - required if not using IAM Roles to authenticate access to S3 buckets   
* `CELERY_BROKER_URL` - Only required if not using IAM Roles for SQS authentication. 
    It must be in the format `sqs://{aws_access_key}:{aws_secret_key}@`.

## Gunicorn settings (_web_ image only)

All [Gunicorn settings](http://docs.gunicorn.org/en/latest/settings.html) may be overridden by an environment variable 
named `GUNICORN_<UPPERCASE-SETTING-NAME>` (e.g. `GUNICORN_WORKERS` overrides `workers`) 

Defaults:

* `GUNICORN_WORKERS` (`workers`): 2

# AWS resources

The application is supposed to run on two separate containers, _web_ and _worker_. 

Each component is completely stateless and it may scale horizontally as required.

## S3 buckets

Two S3 buckets are used for storing files:

1. Media (uploaded) files
2. Static files (images, css, js...)

The _Media_ bucket must be accessible for read&write by both _web_ and _worker_.

The _Static_ bucket must be accessible for read&write by _web_ only 

The _Static_ bucket must also be publicly accessible (from the Internet), either directly (not-recommended)
or through CloudFront CDN (recommended).

`AWS_S3_STATICFILES_CUSTOM_DOMAIN` defines the public DNS domain to access the _Static_ bucket (e.g. the CloudFront domain).

> By default, static files are stored in a `/static` "subdirectory" of the bucket and are expected to be served from 
`https://<AWS_S3_STATICFILES_CUSTOM_DOMAIN>/static/` base URL.

## SQS queue

The application uses an SQS queue named `panelapp` to schedule jobs picked up by _worker_.

It is recommended to create the SQS queue beforehand do not provide the application with permission to create any queues 
(if the queue does not exist the application try to create it, but this is not secure).

The queue **_Visibility Timeout_ must be `360` (seconds)**. 

If _Visibility Timeout_  is different, override the `SQS_QUEUE_VISIBILITY_TIMEOUT` settings to match queue timeout.

> If the _Visibility Timeout_ does not match what the application is expecting, Celery will try to create a new queue 
> and get an error, if it does not have permissions (it should not have)

## Database

The application expects a PostgreSQL-compatible DB: either Aurora or RDS.

## AWS resource security 

Authentication with the database uses username and password (part of `DATABASE_URL`).

Authentication between application and SQS and S3 should use IAM Roles.

No `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` must be explicitly passed to the application (this is not secure!)

### Policy for SQS access

This should be the Least-Privilege IAM Policy to access the SQS Queue.

```
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

### Policy for S3 Media bucket

**TBD**

### Policy for S3 Static bucket and CloudFront CDN

**TBD**

## Logging

All application components logs to console in JSON, using `python3-json-log-formatter==1.6.1` as log formatter, for 
easier log aggregation and indexing.

Logging level is controlled by `DJANGO_LOG_LEVEL` (default = `INFO`). Note that this does not only control Django, but also
Celery and Gunicorn logging.
