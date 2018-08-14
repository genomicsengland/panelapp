FROM python:3.5.5
RUN apt-get update && apt-get install build-essential ntp -y
ENV PYTHONUNBUFFERED 1
RUN mkdir -p /app/panelapp
WORKDIR /app
ADD ./panelapp /app/panelapp/
ADD ./setup.py ./setup.cfg ./MANIFEST.in /app/
RUN pip install . \
    --extra-index-url=https://pypi.gel.zone/root/pypi/+simple/\
    --index-url=https://pypi.gel.zone/genomics/dev\
    --trusted-host=pypi.gel.zone