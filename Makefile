# Makefile for development & CI

.PHONY: help clean docs

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

clean:			## remove python cache files
	find . -name '__pycache__' | xargs rm -rf
	find . -name '*.pyc' -delete
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage

docs:			## build sphinx docs
	@poetry run sphinx-build ./docs ./build/docs


docs-requirements:	## requrement file for docs
	@poetry export -f requirements.txt -E docs --output docs/requirements.txt


version:		## display software version
	@python setup.py --version


install: 		## install packages via poetry
	@./dev/install


lint: 			## run linters
	poetry run ./dev/lint-code


mypy:			## run mypy
	@poetry run mypy openapi


outdated:		## Show outdated packages
	poetry show -o


postgresql:		## run postgresql for testing
	docker run -e POSTGRES_PASSWORD=postgres --rm --network=host --name=openapi-db -d postgres:13


postgresql-nd:		## run postgresql for testing - non daemon
	docker run -e POSTGRES_PASSWORD=postgres --rm --network=host --name=openapi-db postgres:13


test:			## test with coverage
	@poetry run pytest -v -x --cov --cov-report xml --cov-report html


test-version:		## check version compatibility
	@./dev/test-version


test-lint:		## run linters checks
	@./dev/lint-code --check


test-docs: 		## run docs in CI
	make docs


upload-coverage:	## upload coverage
	@poetry run coveralls


publish:		## release to pypi and github tag
	@poetry publish --build -u lsbardel -p $(PYPI_PASSWORD)
