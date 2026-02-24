SHELL := /bin/bash

.PHONY: help
help:
	@echo "Commands:"
	@echo "  make test         - run tests"
	@echo "  make lint         - run linter"
	@echo "  make build        - build docker image"
	@echo "  make push         - push docker image"
	@echo "  make deploy       - deploy to kubernetes"

test:
	pytest

lint:
	flake8 .

build:
	docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/mcp-control-plane:latest .

push:
	docker push ${{ secrets.DOCKERHUB_USERNAME }}/mcp-control-plane:latest

deploy:
	kubectl apply -k k8s/
