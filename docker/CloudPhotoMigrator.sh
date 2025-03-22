#!/bin/bash
# Run CloudPhotoMigrator inside Docker using the current directory
docker run --rm -v "$(pwd):/app" -w /app jaimetur/cloudphotomigrator "$@"
