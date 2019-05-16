# Cloud-native, AWS porting notes

## File storage

Django webapp static files and uploaded files (media) are stored in S3 bucket rather than in file system, using 
[Django S3 Storage](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html).

One limitation of the S3 storage backend is it uses a single S3 bucket for both static and media files.