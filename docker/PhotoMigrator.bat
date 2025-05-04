@echo off
setlocal enabledelayedexpansion

REM Set default values (in case docker.conf doesn't define them)
set "RELEASE_TAG=latest-stable"
set "TZ=UTC"

REM Load variables from docker.conf file if it exists
if exist "docker.conf" (
    for /f "tokens=1,* delims==" %%A in (docker.conf) do (
        set "key=%%A"
        set "value=%%B"
        REM Remove inline comments (anything after #)
        for /f "tokens=1 delims=#" %%C in ("!value!") do (
            set "cleaned=%%C"
        )
        REM Remove any extra spaces
        for /f "tokens=* delims= " %%D in ("!cleaned!") do (
            set "final=%%D"
        )
        if /i "!key!"=="RELEASE_TAG" (
            set "RELEASE_TAG=!final!"
        ) else if /i "!key!"=="TZ" (
            set "TZ=!final!"
        )
    )
)

REM Remove spaces in RELEASE_TAG and TZ if any space
set "RELEASE_TAG=%RELEASE_TAG: =%"
set "TZ=%TZ: =%"

REM Get the current directory
set CURRENT_DIR=%cd%

echo Pulling Docker image: jaimetur/photomigrator:%RELEASE_TAG%
docker pull jaimetur/photomigrator:%RELEASE_TAG%

echo Launching container with TAG='%RELEASE_TAG%' and TZ='%TZ%'...
docker run -it --rm ^
  -v "%CURRENT_DIR%":/docker ^
  -e TZ=%TZ% ^
  jaimetur/photomigrator:%RELEASE_TAG% %*