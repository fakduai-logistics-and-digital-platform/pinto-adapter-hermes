# Hermes Skill: Pinto Chat Adapter

Install the Pinto Chat platform adapter plugin for Hermes Agent.

## What this installs

- **Pinto Chat adapter** — allows Hermes to act as a chatbot on [Pinto](https://pinto-app.com) Thailand.
- Receives webhook events from Pinto and replies via the Pinto Bot API.
- Supports both flat (production) and nested (Swagger) webhook payloads.

## Install steps

```bash
# 1. Copy plugin files to Hermes plugins directory
mkdir -p ~/.hermes/plugins/platforms/pinto
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py
```

## Required environment variables

Add these to your `~/.hermes/.env` file:

```env
PINTO_BOT_ID=your-bot-id-here
```

## Optional environment variables

```env
PINTO_API_URL=https://api.pinto-app.com
PINTO_WEBHOOK_SECRET=your-secret
PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
PINTO_HOME_CHANNEL=default-chat-id
PINTO_ALLOWED_USERS=user-id-1,user-id-2
PINTO_ALLOW_ALL_USERS=true
```

## Dependencies

```bash
pip install httpx
```

## Verify

Restart Hermes and check logs for:

```
Pinto Chat adapter connected (bot_id=your-bot-id)
```

## Uninstall

```bash
rm -rf ~/.hermes/plugins/platforms/pinto
# Remove PINTO_* variables from ~/.hermes/.env
```
