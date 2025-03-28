#!/bin/bash

set -ex

SCRIPT_DIR=$(dirname "$0")

python -m sera.make \
    --app $SCRIPT_DIR/myapp \
    -s $SCRIPT_DIR/schema/product.yml \
    --collection "Product" \
    --collection "Category"