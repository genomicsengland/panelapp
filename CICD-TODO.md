# Collections of ideas for the CI/CD pipeline

## Test stage

The following snipped may be part of the GilLab CI definition for the Test stage, assuming the root directory of this 
application project is in the working directory:

```yaml
image: python:3.6.8-alpine3.9
services:
  - postgres:9.6.9
script:
  - apk add --no-cache postgresql-libs curl jpeg-dev zlib-dev gcc musl-dev curl-dev postgresql-dev build-base linux-headers
  - pip install .[dev,tests]
  - pip install pytest-runner
  - pytest
```

`apk add...` may be moved to a base image, to be used by all builds, to save some time.

**The base `image` must be the same used in the [application base dockerfile](docker/cloud/Dockerfile-base)**

**The PostgreSQL version must match the version of Aurora PostgreSQL**
