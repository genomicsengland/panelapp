# Cloud-native, AWS porting notes

## File storage

Django webapp static files and uploaded files (media) are stored in S3 bucket rather than in file system, using 
[Django S3 Storage](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html).

One limitation of S3 Storage is it uses a 
[single S3 bucket for both static and media files](https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/).
`S3Boto3Storage` has been extended to use separate buckets and possibly different configurations.
