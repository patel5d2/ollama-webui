# Ollama + Open WebUI

Open http://localhost:3000 and create your first account (the administrator).
Ollama's API is at http://localhost:11434. Both ports are bound to localhost.
Open WebUI connects to Ollama through the private Compose network.

From this directory:

```sh
docker compose up -d       # start
docker compose stop       # stop, retaining data
docker compose ps         # status
docker compose logs -f    # logs
docker compose pull       # download updated images
docker compose up -d      # apply updates
```

Download a model before chatting, through Open WebUI's model management or:

```sh
docker compose exec ollama ollama pull llama3.2:1b
```

Models and application data are stored in the `ollama-webui_ollama` and
`ollama-webui_open-webui` Docker volumes. Do not use `docker compose down -v`
unless you intend to delete those volumes. Keep `.env` private; it stores the
application's persistent signing key.

Containers restart with Docker unless explicitly stopped. Docker Desktop must
be running. Ollama inside Docker on macOS uses CPU rather than Apple GPU
acceleration.
# ollama-webui
