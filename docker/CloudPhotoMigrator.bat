@echo off
setlocal enabledelayedexpansion

REM Set default values (in case docker.conf doesn't define them)
set "RELEASE_TAG=latest"
set "TZ=UTC"

REM Load variables from docker.conf file if it exists
if exist "docker.conf" (
    for /f "usebackq tokens=1,* delims==" %%A in ("docker.conf") do (
        if /i "%%A"=="RELEASE_TAG" (
            REM El segundo token %%B puede contener inline comments. Ej: Europe/Madrid # comentario
            for /f "usebackq tokens=1 delims=#" %%X in ("%%B") do (
                set "RELEASE_TAG=%%~X"
            )
        ) else if /i "%%A"=="TZ" (
            REM Lo mismo para TZ
            for /f "usebackq tokens=1 delims=#" %%X in ("%%B") do (
                set "TZ=%%~X"
            )
        )
    )
)

REM Remove spaces in RELEASE_TAG and TZ if any space
set "RELEASE_TAG=%RELEASE_TAG: =%"
set "TZ=%TZ: =%"

REM Get the current directory
set CURRENT_DIR=%cd%

echo 🐳 Pulling Docker image: jaimetur/cloudphotomigrator:%RELEASE_TAG%
docker pull jaimetur/cloudphotomigrator:%RELEASE_TAG%

echo 🚀 Launching container with tag: %RELEASE_TAG%
docker run -it --rm ^
  -v "%CURRENT_DIR%":/docker ^
  -e TZ=%TZ% ^
  jaimetur/cloudphotomigrator:%RELEASE_TAG% %*