#!/usr/bin/env make
# Created by sebastientourbier on 2023-10-20
.DEFAULT_GOAL := help

# Set environment variables for the docker image name and tag
IMAGE_NAME=astral-ctp-anonymizer

TAG=0.0.1

$(info TAG = $(TAG))
# Replace +, /, _ with - to normalize the tag
# in case the tag includes a branch name
override TAG := $(subst +,-,$(TAG))
override TAG := $(subst /,-,$(TAG))
override TAG := $(subst _,-,$(TAG))
$(info TAG (Normalized) = $(TAG))

IMAGE_TAG=$(IMAGE_NAME):$(TAG)

# Define the build date and vcs reference
BUILD_DATE = $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF = $(shell git rev-parse --short HEAD)

#build-docker: @ Builds the Docker image
build-docker:
	docker build \
		-f docker/astral-ctp-anonymizer/Dockerfile \
		-t $(IMAGE_TAG) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg VCS_REF=$(VCS_REF) \
		--build-arg VERSION=$(TAG) .

#help:	@ List available make command for this project
help:
	@grep -E '[a-zA-Z\.\-]+:.*?@ .*$$' $(MAKEFILE_LIST)| tr -d '#'  | awk 'BEGIN {FS = ":.*?@ "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
