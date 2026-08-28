#!/usr/bin/env bash

set -e

IMAGE_TAG_NAME=erp_api
PACKAGE_NAME=erp_api

ROOT_DIR_PATH=$(realpath "$(dirname -- "$0")/../")

VERSION_REGEX='(?!.*\.(\.|"|\+))VERSION = "\K\d+(?:\.\d+){2}(?:-[0-9A-Za-z-.]+)*(?:\+[0-9A-Za-z-.]+)?(?=")'

set +e
VERSION=$(grep -oP "$VERSION_REGEX" "$ROOT_DIR_PATH/src/$PACKAGE_NAME/version.py")
if [ -z "$VERSION" ]; then
  echo "ERRO: versão não encontrada em '$ROOT_DIR_PATH/src/$PACKAGE_NAME/version.py'"
  exit 1
fi
set -e

echo " - Image tag:  $IMAGE_TAG_NAME"
echo " - Version:    $VERSION"

set -x

docker build \
  -t "$IMAGE_TAG_NAME:latest" \
  -t "$IMAGE_TAG_NAME:$VERSION" \
  "$ROOT_DIR_PATH"
