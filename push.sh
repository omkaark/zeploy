#!/bin/bash

# Take cli arg 1 (docker_image:tag)
TAGGED_IMAGE=$1
IMAGE=$(echo "$TAGGED_IMAGE" | cut -d ':' -f1)

# Creating directory in images
DIR="./file_server/images/$IMAGE"
echo "Creating $DIR directory"
rm -rf "$DIR" && mkdir -p "$DIR"

# Export container to tar
echo "Exporting $TAGGED_IMAGE under $DIR/$IMAGE.tar"
CREATED_CONTAINER=$(docker create "$TAGGED_IMAGE")
docker export "$CREATED_CONTAINER" > "$DIR/$IMAGE.tar" 
docker rm "$CREATED_CONTAINER"

# Unpack tar and populate the folder
tar -C "$DIR" -xf "$DIR/$IMAGE.tar"
rm -rf "$DIR/$IMAGE.tar"

# Get container configuration
CONFIG=$(docker inspect "$TAGGED_IMAGE")

# Extract ARG_LIST, ENV_LIST, and WORKDIR from config
ARG_LIST=$(echo "$CONFIG" | jq -r '.[0].Config.Cmd | @json')
ENV_LIST=$(echo "$CONFIG" | jq -r '.[0].Config.Env | @json')
WORKDIR=$(echo "$CONFIG" | jq -r '.[0].Config.WorkingDir')

# Escape special characters for sed
ARG_LIST_ESCAPED=$(echo "$ARG_LIST" | sed 's/[\/&]/\\&/g')
ENV_LIST_ESCAPED=$(echo "$ENV_LIST" | sed 's/[\/&]/\\&/g')
WORKDIR_ESCAPED=$(echo "$WORKDIR" | sed 's/[\/&]/\\&/g')

# Write the correct config.json
cp config.template.json "$DIR/config.json"
sed -i.bak \
    -e "s|\"ARG_LIST\"|$ARG_LIST_ESCAPED|g" \
    -e "s|\"ENV_LIST\"|$ENV_LIST_ESCAPED|g" \
    -e "s|\"WORKING_DIR\"|\"$WORKDIR_ESCAPED\"|g" \
    "$DIR/config.json"

echo "Process completed successfully."