# 11. Docler Deployment

This section summarizes the two supported Docker deployment modes for PhotoMigrator.

---

## 11.1 Deploy Web Interface with Docker Compose

Use this mode if you want the browser-based UI.

- Docker image: `jaimetur/photomigrator`
- Recommended files:
  - `docker-web/docker-compose.yml`
  - `docker-web/.env`
- Default access:
  - `http://localhost:6078`

Main guide:

- [Deploy Web Interface from Docker](/docs/view/help/docker-deployments/deploy-web-interface-from-docker.md)

Typical startup:

```bash
docker compose pull
docker compose up -d
```

Use this mode when you want:

- the visual web interface
- multi-user access
- job execution from the browser
- integrated logs and help viewer

---

## 11.2 Deploy CLI Interface with Docker

Use this mode if you want to run PhotoMigrator commands directly from the terminal.

- Docker image: `jaimetur/photomigrator-linux`
- Supported ways:
  - packaged launcher (`docker-cli/PhotoMigrator.sh` / `PhotoMigrator.bat`)
  - direct `docker run`

Main guide:

- [Deploy CLI Interface from Docker](/docs/view/help/docker-deployments/deploy-cli-interface-from-docker.md)

Typical help command:

```bash
docker run --rm -v "$(pwd)":/docker -e TZ=Europe/Madrid jaimetur/photomigrator-linux:latest-stable -h
```

Use this mode when you want:

- direct CLI execution
- scripting or cron jobs
- headless runs
- terminal-first workflows

---

## 11.3 Which one should I use?

- Choose `Web Interface` if you want an interactive UI in the browser.
- Choose `CLI Interface` if you want direct command-line usage or automation.

Related guides:

- [Deploy Web Interface from Docker](/docs/view/help/docker-deployments/deploy-web-interface-from-docker.md)
- [Deploy CLI Interface from Docker](/docs/view/help/docker-deployments/deploy-cli-interface-from-docker.md)
