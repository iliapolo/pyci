SHELL := /bin/bash

PROJECT_NAME=$(shell dirname "$0")
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

.PHONY: test help
.DEFAULT_GOAL := ci

ci: dep lint test ## Equivelant to 'make dep lint test'

help: ## Show this help message.

	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

dep: dep-test dep-project ## Equivelant to 'make dep-test dep-project'

dep-test: ## Install the dependent libraries needed for tests.

	pip install -r test-requirements.txt

dep-project: ## Install the dependent libraries needed for the project to run.

	pip install -e .

lint: dep ## Run lint validations.

	pylint --rcfile pylint.ini pyci

test-unit: dep ## Run the unit tests.

	py.test --junitxml=reports/test/pytest/junit.xml -s --durations=10 -v -m "not cross_distro" -rs -c pytest.ini  --cov-config=coverage.ini --cov=pyci pyci/tests --rootdir .

test-cross-distro: dep ## Run the cross-distro tests.

	py.test --junitxml=reports/test/pytest/junit.xml -s --durations=10 -v -m cross_distro -rs -c pytest.ini pyci/tests --rootdir .

test: test-unit test-cross-distro ## Equivelant to 'make test-unit test-cross-distro'

release: dep-project ## Run release

	pyci release --wheel-universal --binary-entrypoint pyci.spec

codecov: ## Report coverage to codecov.io

	bash <(curl -s https://codecov.io/bash) -Z