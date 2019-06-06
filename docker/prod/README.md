# Production docker

This directory contains Dockerfiles for generating images to be used in all AWS environments (as opposed to local development).

It is designed to run on AWS, using S3 and SQS (as opposed to file-system storage and RabbitMQ).

The Django settings module must be `panelapp.settings.docker-aws` (`DJANGO_SETTINGS_MODULE=panelapp.settings.docker-aws`).

Different environments (e.g. Staging, Prod) are configured setting the environment variables below.

Configurations of _web_ and _worker_ containers should be the same, except those related to Gunicorn only used in _web_.

To configure it for running with LocalStack, look at the comments in `panelapp/panleapp/settings/docker-aws.py`.

##  Mandatory environment variables

All of the following must be explicitly configured

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

# Production environment requirements

By default, the prod, dockerised application is supposed to be deployed on AWS.

It runs as two separate components (containers): _web_ and _worker_. 

Each component is completely stateless and it may scale horizontally as required.

## S3 

We two S3 buckets for storing files:

1. Media (uploaded) files
2. Static files (images, css, js...)

The _Media_ bucket must be accessible by both _web_ and _worker_.

The _Static_ bucket must be accessible by _web_ only but must be exposed to the Internet, either directly (not-recommended)
or through CloudFront CDN (recommended).

The external domain the _Static_ bucket is accessible at must be specified in the `AWS_S3_STATICFILES_CUSTOM_DOMAIN` setting.

> By default, static files are stored in a `/static` "subdirectory" of the bucket and are expected to be served from 
`https://<AWS_S3_STATICFILES_CUSTOM_DOMAIN>/static/` base URL.

## SQS

The application uses an SQS queue named `panelapp` to schedule jobs picked up by _worker_.

It is recommended to create the SQS queue beforehand do not provide the application with permission to create any queues 
(if the queue does not exist the application try to create it, but this is not secure).

The SQS queue _Visibility Timeout_ must be `360` (seconds). 
If different, override the `SQS_QUEUE_VISIBILITY_TIMEOUT` to match the queue _Visibility Timeout_.

> If the _Visibility Timeout_ does not match what the application is expecting, Celery will try to create a new queue 
> and get an error, if it does not have permissions (it should not have)

## Database

The application expects a PostgreSQL-compatible DB: either Aurora or RDS.

## Internal authentication 

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
