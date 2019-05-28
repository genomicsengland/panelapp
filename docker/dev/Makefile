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
	docker-compose build

up: ## Run cluster
	docker-compose up -d

migrate: ## Create db schema, apply db migration (migrate command)
	docker-compose exec web python manage.py migrate

loaddata: ## Load genes files into db (loaddata command)
	docker-compose exec web python manage.py loaddata /app/genes.json

collectstatic: ## Deploy static files (collectstatic command)
	docker-compose exec web python manage.py collectstatic --noinput

createsuperuser: ## Create superuser (interactively insert password)
	docker-compose exec web python manage.py createsuperuser --username admin --email adimin@test.test

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
mock-aws: export AWS_ACCESS_KEY_ID := foo
mock-aws: export AWS_SECRET_ACCESS_KEY := bar
mock-aws: .mock-s3-static .mock-s3-media .mock-sqs-queue ## Create all mock AWS resources (docker-compose cluster must be running)


help:	## display this help
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

.mock-s3-static: ## Create mock S3 bucket for static files
	$(call create-s3-bucket-if-not-exits,static)

.mock-s3-media: ## Create mock S3 bucket for media files
	$(call create-s3-bucket-if-not-exits,media)

.mock-sqs-queue: ## Create mock SQS queue for Celery
	@echo "Create sqs://panelapp if not exists"
	@aws --endpoint-url=http://localhost:4576 sqs create-queue --queue-name panelapp --attributes VisibilityTimeout=360 --output text

.PHONY:	clean .copy_sources run down-cluster migrate load-genes collect-static build-dev-env stop start down-cluster
.DEFAULT_GOAL:=help
