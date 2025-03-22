@echo off
:: Run CloudPhotoMigrator inside Docker using the current directory
docker run --rm -v "%cd%:/app" -w /app jaimetur/cloudphotomigrator %*
