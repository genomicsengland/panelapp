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

build: clean .copy_sources ## Build Docker Images
	docker-compose build

run: ## Run cluster
	docker-compose up -d

migrate: ## Create db schema, apply db migration (migrate command)
	docker-compose exec web python manage.py migrate

loaddata: ## Load genes files into db (loaddata command)
	docker-compose exec web python manage.py loaddata /app/genes.json

collectstatic: ## Deploy static files (collectstatic command)
	docker-compose exec web python manage.py collectstatic --noinput

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

command: ## Run a generic command, passed as additional argument(s)
	docker-compose exec web python manage.py $(COMMAND_ARGS)

mock-aws: export AWS_DEFAULT_REGION := eu-west-2
mock-aws: export AWS_ACCESS_KEY_ID := foo
mock-aws: export AWS_SECRET_ACCESS_KEY := bar
mock-aws: .mock-s3-static .mock-s3-media ## Create all mock AWS resources (docker-compose cluster must be running)


help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target> [<arguments>]\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

# Helpers

$(BUILDDIR):
	mkdir -p $(BUILDDIR)/$(APPDIR)

.copy_sources: $(BUILDDIR)
	cp -r $(SOURCEDIR)/panelapp/* $(BUILDDIR)/panelapp/
	cp $(SOURCEDIR)/setup.py $(SOURCEDIR)/setup.cfg $(SOURCEDIR)/MANIFEST.in $(SOURCEDIR)/VERSION $(SOURCEDIR)/deploy/* $(BUILDDIR)/


.mock-s3-static: ## Create mock S3 bucket for static files
	aws configure set default.s3.addressing_style path
	aws --endpoint-url=http://localhost:4572 s3 mb s3://static
	aws --endpoint-url=http://localhost:4572 s3api put-bucket-acl --bucket static --acl public-read

.mock-s3-media: ## Create mock S3 bucket for media files
	aws configure set default.s3.addressing_style path
	aws --endpoint-url=http://localhost:4572 s3 mb s3://media
	aws --endpoint-url=http://localhost:4572 s3api put-bucket-acl --bucket media --acl public-read


.PHONY:	clean .copy_sources run down-cluster migrate load-genes collect-static build-dev-env stop start down-cluster
.DEFAULT_GOAL:=help
