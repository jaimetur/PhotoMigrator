@echo off
REM Get the current directory
set CURRENT_DIR=%cd%

REM Pull the latest version of the Docker image to avoid using a cached one
docker pull jaimetur/cloudphotomigrator:latest

REM Run the Docker container with the current directory mounted to /data
docker run --rm -v "%CURRENT_DIR%":/data jaimetur/cloudphotomigrator:latest %*
