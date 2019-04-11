FROM python:3.5-jessie
RUN apt-get update && apt-get install build-essential ntp -y
ENV PYTHONUNBUFFERED 1
RUN mkdir -p /app/panelapp
WORKDIR /app
ADD ./panelapp /app/panelapp/
ADD ./setup.py ./setup.cfg ./MANIFEST.in ./VERSION /app/
RUN pip install -e .
