# Production docker

This directory contains Dockerfiles for generating images to be used in **all** deployed environments (as opposed to local development).

All defaults are for running it on AWS (using AWS services like S3 and SQS) but it may be switched back to using RabbitMQ
and file system (not quite "cloud-native").

# Required environment variables

## Non-Secrets

* `AWS_S3_STATICFILES_BUCKET_NAME` - Name of the S3 bucket for storing static files
* `AWS_S3_MEDIAFILES_BUCKET_NAME` - Name of the S3 bucket for storing media (uploaded) files
* `AWS_REGION` - AWS Region
* `AWS_S3_STATICFILES_CUSTOM_DOMAIN` - Custom CDN domain to serve static files from (e.g. `cdn.mydomain.com` - no trailing `/`)
* `AWS_S3_MEDIAFILES_CUSTOM_DOMAIN` - Custom CDN domain to serve media (uploaded) files from (if any)
* `ALLOWED_HOSTS` - whitelisted hostnames, if user tries to access website which isn't here Django will throw 500 error
* `DEFAULT_FROM_EMAIL` - we send emails as this address
* `PANEL_APP_EMAIL` - PanelApp email address
* `EMAIL_HOST` - SMTP host 
* `EMAIL_PORT` - SMTP server port

## Secrets

* `DATABASE_URL` - PostgreSQL config url, in the format: `postgresql://{username}:{password}@{host}:{port}/{database_name}`
* `DJANGO_ADMIN_URL` - change admin URL to something secure.
* `EMAIL_HOST_USER` - SMTP username
* `EMAIL_HOST_PASSWORD` - SMTP password
* `HEALTH_CHECK_TOKEN` - Token to authenticate health check endpoint requests
* `SECRET_KEY` - Secret for encrypting cookies


# Other optional environment variables

## Non-secrets

* `USE_SQS=FALSE` - to disable SQS as Celery backend, and use a RabbitMQ instance instead. Must also override `CELERY_BROKER_URL`
* `USE_S3=FALSE` - to disable storing static and media files on S3 and using the local file system instead
* `DJANGO_LOG_LEVEL` - to override Django log-level (default=`INFO`)
* `EMAIL_USE_TLS` - Set to False to prevent SMTP from using TLS
* `STATIC_ROOT` and `MEDIA_ROOT` - **only if `USE_S3=FALSE`**, file system location for static and media (uploaded) file, 
    respectively (default `/static` and `/media`) \
* `AWS_STATICFILES_LOCATION` - Path (key) that will contain static files, in the S3 bucket
* `SQS_QUEUE_VISIBILITY_TIMEOUT` - SQS topic _Visibility Timeout_. Must be identical to the Visibility Timeout of the SQS queue
* `TASK_QUEUE_NAME` - Name of the SQS queue (default: `panelapp`)     

## Secrets

* `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` - required if not using IAM Roles to authenticate access to S3 buckets   
* `CELERY_BROKER_URL` - if not using IAM Roles for SQS authentication, this must be in the format 
    `sqs://{aws_access_key}:{aws_secret_key}@`, or `amqp://{username}:{password}@{host}:{port}/{virtual}` if `USE_SQS` 
    is set to `FALSE` to use RabbitMQ instead of SQS

## Gunicorn settings

All [Gunicorn settings](http://docs.gunicorn.org/en/latest/settings.html) may be overridden by an environment variable 
named `GUNICORN_<UPPERCASE-SETTING-NAME>` (e.g. `GUNICORN_WORKERS` overrides `workers`) 

Defaults:

* `GUNICORN_WORKERS` (`workers`): 2

# Production environment requirements

By default, the prod, dockerised application is supposed to be deployed on AWS.

It uses S3 for storing static and media files and SQS as Celery backend.

It expects two separate S3 buckets and an SQS named `panelapp`. 

It the SQS queue exists (suggested) the application does not try to create it. O

The SQS queue _Visibility Timeout_ must be `360` (seconds). If different, you must override the `SQS_QUEUE_VISIBILITY_TIMEOUT`
to match the queue _Visibility Timeout_ or the Worker application will throw an error on start.

By default, SQS and S3 authentication uses IAM Roles. Alternatively, set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` 
(not advisable).

If `USE_S3` = `FALSE` static and media files go on the file system, at the paths defined by `STATIC_ROOT` and `MEDIA_ROOT`
(default: `/static` and `/media`).


## AWS 

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

Note the default queue name is `panelapp` unless overridden.
