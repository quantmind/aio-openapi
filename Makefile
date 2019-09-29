.PHONY: help

help:
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

clean:		## remove python cache files
	find . -name '__pycache__' | xargs rm -rf
	find . -name '*.pyc' -delete
	rm -rf build
	rm -rf dist
	rm -rf aio-openapi.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage

version:	## dipsplay software version
	@python3 -c "import openapi; print(openapi.__version__)"

isort: 		## run isort
	@isort -rc

black: 		## run black and fix files
	@./dev/run-black.sh


black-check: 	## run black check in CI
	@./dev/run-black.sh --check


mypy:		## run mypy
	@mypy openapi
