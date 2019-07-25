#################################################################
# This Makefile is for troubleshooting production images locally.
# It is not meant to build, deploy or run any actual environment!
#################################################################

BUILDDIR := .build
APPDIR :=  panelapp
SOURCEDIR := ../..

# If the first argument is "command"...
ifeq (command,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "command"
  COMMAND_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(COMMAND_ARGS):;@:)
endif

# LocalStack needs a different TMPDIR in OSX
OS := $(shell uname)
TMPDIR := /tmp/localstack
ifeq ($(OS),Darwin)
  TMPDIR := /private$(TMPDIR)
endif
export TMPDIR := $(TMPDIR)

clean: ## Remove build directory
	rm -rf $(BUILDDIR)

build: clean ## Build Docker Images
	cd ../.. ; docker build --tag panelapp-base --file ./docker/cloud/Dockerfile-base . ; cd docker/cloud
	docker-compose build

up: ## Run cluster
	docker-compose up -d

migrate: ## Create db schema, apply db migration (migrate command)
	docker-compose exec web python manage.py migrate

loaddata: export AWS_ACCESS_KEY_ID := dummy-key
loaddata: export AWS_SECRET_ACCESS_KEY := dummy-secret
loaddata: ## Load genes files into db (loaddata command)
	aws --endpoint-url=http://localhost:4572 s3 cp ../../deploy/genes.json.gz s3://media-bucket/genes.json.gz
	docker-compose exec web /bin/sh -c "python -c \"import boto3,botocore;boto3.resource('s3',use_ssl=False, endpoint_url='http://localstack:4572').Bucket('media-bucket').download_file('genes.json.gz', '/var/tmp/genes.json.gz')\"; python manage.py loaddata --verbosity 3 /var/tmp/genes.json; rm /var/tmp/genes.json.gz"
	aws --endpoint-url=http://localhost:4572 s3 rm s3://media-bucket/genes.json.gz


collectstatic: ## Deploy static files (collectstatic command)
	docker-compose exec web python manage.py collectstatic --noinput

createsuperuser: ## Create superuser (username: 'admin', pwd: 'changeme', email: `admin@local`)
	docker-compose exec web /bin/sh -c "echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@local', 'changeme')\" | python manage.py shell"

command: ## Run a generic command, passed as additional argument(s)
	docker-compose exec web python manage.py $(COMMAND_ARGS)

stop: ## Stop cluster, without destroying it
	docker-compose stop

start: ## Restart a stopped cluster
	docker-compose start

down: ## Destroy cluster
	docker-compose down

tests: ## Run tests
	docker-compose exec web bash -c 'cd /app ; pytest'

logs: ## Tail all logs
	docker-compose logs -f

mock-aws: export AWS_DEFAULT_REGION := eu-west-2
mock-aws: export AWS_ACCESS_KEY_ID := dummy-key
mock-aws: export AWS_SECRET_ACCESS_KEY := dummy-secret
mock-aws: .mock-s3-static .mock-s3-media .mock-sqs-queue ## Create all mock AWS resources

clear-s3: ## Clear mock S3 buckets
	rm -rf $(TMPDIR)/*

help:	## display this help
	@echo "************************************************"
	@echo "This makefile is for local troubleshooting only"
	@echo "   THIS IS NOT FOR RUNNING PRODUCTION IMAGES"
	@echo "************************************************"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target> [<arguments>]\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

# Helpers

$(BUILDDIR):
	mkdir -p $(BUILDDIR)/$(APPDIR)

define create-s3-bucket-if-not-exits
	@echo "Create s3://$(1) if not exists"
	@aws configure set default.s3.addressing_style path
	@aws --endpoint-url=http://localhost:4572 s3 mb s3://$(1) 2>/dev/null || true
	@aws --endpoint-url=http://localhost:4572 s3api put-bucket-acl --bucket $(1) --acl public-read
endef

define create-sqs-queue-if-not-exists
	@echo "Create sqs queue '$(1)' if not exists"
	@aws --endpoint-url=http://localhost:4576 sqs create-queue --queue-name $(1) --attributes VisibilityTimeout=360 2>/dev/null || true
endef

.mock-s3-static: ## Create mock S3 bucket for static files
	$(call create-s3-bucket-if-not-exits,static-bucket)

.mock-s3-media: ## Create mock S3 bucket for media files
	$(call create-s3-bucket-if-not-exits,media-bucket)

.mock-sqs-queue: ## Create mock SQS queue for Celery
	$(call create-sqs-queue-if-not-exists,panelapp)

.PHONY:	clean .copy_sources .mock-s3-static .mock-s3-media .mock-sqs-queue up down migrate loaddata collectstatic stop start mock-aws createsuperuser command tests logs clear-s3
.DEFAULT_GOAL:=help
