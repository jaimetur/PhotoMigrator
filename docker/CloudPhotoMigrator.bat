@echo off
REM Get the current directory
set CURRENT_DIR=%cd%

REM Run the Docker container with the current directory mounted to /data
docker run --rm -v "%CURRENT_DIR%":/data jaimetur/cloudphotomigrator:latest %*
