#! /usr/bin/env sh

# Exit in case of error
set -e
set -x

pytest --cov=erp_api --cov-report=term-missing tests
