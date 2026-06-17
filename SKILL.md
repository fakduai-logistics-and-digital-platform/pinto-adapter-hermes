1|# Hermes Skill: Pinto Chat Adapter
2|
3|Install the Pinto Chat platform adapter plugin for Hermes Agent.
4|
5|## What this installs
6|
7|- **Pinto Chat adapter** — allows Hermes to act as a chatbot on [Pinto](https://pinto-app.com) Thailand.
8|- Receives webhook events from Pinto and replies via the Pinto Bot API.
9|- Supports both flat (production) and nested (Swagger) webhook payloads.
10|
11|## Install steps
12|
13|```bash
14|# 1. Copy plugin files to Hermes plugins directory
15|mkdir -p ~/.hermes/plugins/platforms/pinto
16|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
17|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
18|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py
19|```
20|
21|## Bot ID config
22|
23|Preferred durable config in `~/.hermes/config.yaml`:
24|
25|```yaml
26|platforms:
27|  pinto:
28|    enabled: true
29|    extra:
30|      botId: your-bot-id-here
31|```
32|
33|Fallback/standalone setup in `~/.hermes/.env`:
34|
35|```env
36|PINTO_BOT_ID=your-bot-id-here
37|```
38|
39|If both exist, keep `config.yaml` as source of truth and treat `PINTO_BOT_ID` as fallback.
40|
41|## Optional environment variables
30|
31|```env
32|PINTO_API_URL=https://api.pinto-app.com
33|PINTO_WEBHOOK_SECRET=your-secret
34|PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
35|PINTO_HOME_CHANNEL=default-chat-id
36|PINTO_ALLOWED_USERS=user-id-1,user-id-2
37|PINTO_ALLOW_ALL_USERS=true
38|```
39|
40|## Dependencies
41|
42|```bash
43|pip install httpx
44|```
45|
46|## Verify
47|
48|Restart Hermes and check logs for:
49|
50|```
51|Pinto Chat adapter connected (bot_id=your-bot-id)
52|```
53|
54|## Uninstall
55|
56|```bash
57|rm -rf ~/.hermes/plugins/platforms/pinto
58|# Remove PINTO_* variables from ~/.hermes/.env
59|```
60|