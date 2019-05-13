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

OS := $(shell uname)
ifeq ($(OS),Darwin)
  ## LocalStack needs a different TMPDIR in OSX
  TMPDIR := /private$(TMPDIR)
endif

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

stop: ## Stop cluster, withoud destroying
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


help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target> [<arguments>]\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

# Helpers

$(BUILDDIR):
	mkdir -p $(BUILDDIR)/$(APPDIR)

.copy_sources: $(BUILDDIR)
	cp -r $(SOURCEDIR)/panelapp/* $(BUILDDIR)/panelapp/
	cp $(SOURCEDIR)/setup.py $(SOURCEDIR)/setup.cfg $(SOURCEDIR)/MANIFEST.in $(SOURCEDIR)/VERSION $(SOURCEDIR)/deploy/* $(BUILDDIR)/

.PHONY:	clean .copy_sources run down-cluster migrate load-genes collect-static build-dev-env stop start down-cluster
.DEFAULT_GOAL:=help
