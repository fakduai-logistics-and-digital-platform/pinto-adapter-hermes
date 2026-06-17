# 🫓 Hermes Pinto Chat Adapter

<img width="1672" alt="image" src="https://github.com/user-attachments/assets/c4ceaa39-1cf5-437a-8ce1-f97a5b67961d" />


**Pinto Chat** platform adapter plugin for [Hermes Agent](https://github.com/nousresearch/hermes-agent).

Allows Hermes to act as a chatbot on [Pinto](https://pinto-app.com), a Thai social platform. The adapter receives webhook events from Pinto and replies through the Pinto Bot API.

---

## 🇹🇭 ภาษาไทย

### คืออะไร?

Plugin นี้ทำให้ **Hermes Agent** สามารถทำงานเป็นแชทบอทบนแอป **Pinto** ได้ โดยรองรับรูปแบบ payload ทั้ง 2 แบบ:

* **Flat payload** สำหรับ Production — `message` เป็น string ธรรมดา
* **Nested payload** ตาม Swagger spec — `message` เป็น object ที่มี `content` และ `sender`

---

### ติดตั้ง

#### วิธีที่ 1: ใช้ Hermes Skills

```bash
hermes skills install https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/SKILL.md
```

#### วิธีที่ 2: ติดตั้งเอง

```bash
mkdir -p ~/.hermes/plugins/platforms/pinto

curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py

pip install httpx
```

---

### ตั้งค่า

ตั้งค่าแนะนำแบบถาวรใน `~/.hermes/config.yaml`:

```yaml
platforms:
  pinto:
    enabled: true
    extra:
      botId: your-pinto-bot-id
      apiUrl: https://api.pinto-app.com
      webhookSecret: your-secret-key
      webhookPath: /plugins/pinto/webhook
```

หรือใช้ environment variables ใน `~/.hermes/.env` เป็น fallback/standalone setup:

```env
PINTO_BOT_ID=your-pinto-bot-id
PINTO_API_URL=https://api.pinto-app.com
PINTO_WEBHOOK_SECRET=your-secret-key
PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
PINTO_HOME_CHANNEL=chat-id-for-cron
PINTO_ALLOWED_USERS=user-id-1,user-id-2
PINTO_ALLOW_ALL_USERS=true
```

ถ้า `config.yaml` มี `platforms.pinto.extra.botId` แล้ว ให้ถือค่านั้นเป็นค่าหลัก; `PINTO_BOT_ID` เป็น fallback ตอน config ยังไม่มี botId เท่านั้น.

#### Environment variables

| Variable                | Required | Description                                       |
| ----------------------- | -------: | ------------------------------------------------- |
| `PINTO_BOT_ID`          |       No | fallback Bot ID เมื่อ `config.yaml` ยังไม่มี botId |
| `PINTO_API_URL`         |       No | Base URL ของ Pinto API                            |
| `PINTO_WEBHOOK_SECRET`  |       No | Secret สำหรับตรวจสอบ webhook                      |
| `PINTO_WEBHOOK_PATH`    |       No | Path สำหรับรับ webhook                            |
| `PINTO_HOME_CHANNEL`    |       No | Chat ID สำหรับ cron หรือ scheduled messages       |
| `PINTO_ALLOWED_USERS`   |       No | รายชื่อ user ID ที่อนุญาตให้ใช้งาน คั่นด้วย comma |
| `PINTO_ALLOW_ALL_USERS` |       No | อนุญาตให้ทุก user ใช้งานบอท                       |

---

### ทดสอบแบบ Standalone

สามารถทดสอบโดยไม่ต้องใช้ Hermes Gateway ได้

```bash
cp .env.example .env
python pinto_webhook_server.py
```

หรือระบุ tunnel URL:

```bash
python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
```

---

## 🇬🇧 English

### What is this?

This plugin allows **Hermes Agent** to function as a chatbot on **Pinto**. It supports both webhook payload formats:

* **Flat payload** for Production — `message` is a plain string
* **Nested payload** from the Swagger spec — `message` is an object with `content` and `sender`

---

### Install

#### Option 1: Use Hermes Skills

```bash
hermes skills install https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/SKILL.md
```

#### Option 2: Manual install

```bash
mkdir -p ~/.hermes/plugins/platforms/pinto

curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py

pip install httpx
```

---

### Configure

Recommended persistent config in `~/.hermes/config.yaml`:

```yaml
platforms:
  pinto:
    enabled: true
    extra:
      botId: your-pinto-bot-id
      apiUrl: https://api.pinto-app.com
      webhookSecret: your-secret-key
      webhookPath: /plugins/pinto/webhook
```

Or use environment variables in `~/.hermes/.env` as a fallback/standalone setup:

```env
PINTO_BOT_ID=your-pinto-bot-id
PINTO_API_URL=https://api.pinto-app.com
PINTO_WEBHOOK_SECRET=your-secret-key
PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
PINTO_HOME_CHANNEL=chat-id-for-cron
PINTO_ALLOWED_USERS=user-id-1,user-id-2
PINTO_ALLOW_ALL_USERS=true
```

If `config.yaml` already has `platforms.pinto.extra.botId`, treat that value as primary; `PINTO_BOT_ID` is only a fallback when config has no botId yet.

#### Environment variables

| Variable                | Required | Description                                        |
| ----------------------- | -------: | -------------------------------------------------- |
| `PINTO_BOT_ID`          |       No | fallback Bot ID when `config.yaml` has no botId    |
| `PINTO_API_URL`         |       No | Pinto API base URL                                 |
| `PINTO_WEBHOOK_SECRET`  |       No | Secret used to validate webhook requests           |
| `PINTO_WEBHOOK_PATH`    |       No | Webhook path used by the adapter                   |
| `PINTO_HOME_CHANNEL`    |       No | Chat ID for cron or scheduled messages             |
| `PINTO_ALLOWED_USERS`   |       No | Comma-separated list of allowed user IDs           |
| `PINTO_ALLOW_ALL_USERS` |       No | Allows all users to interact with the bot          |

---

### Standalone Testing

You can test the adapter without Hermes Gateway.

```bash
cp .env.example .env
python pinto_webhook_server.py
```

Or specify a tunnel URL:

```bash
python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
```

---

## Webhook Payload Formats

### Flat Payload

Production payload format:

```json
{
  "user_id": "d5670660-df19-4c04-b042-c07c1005ae38",
  "username": "hermes",
  "message": "ไง hermes",
  "chat_id": "232d5b28-ba79-4ba8-98c9-6399dcb300e7",
  "bot_id": "hermes_ai"
}
```

In this format, `message` is a string.

---

### Nested Payload

Swagger payload format:

```json
{
  "bot_id": "hermes_ai",
  "chat_id": "...",
  "message": {
    "chat_id": "...",
    "content": "Hello!",
    "sender": {
      "user_id": "...",
      "username": "user",
      "name": "User"
    }
  }
}
```

In this format, `message` is an object that contains `content` and `sender`.

---

## Reply API

The adapter sends replies to Pinto through this endpoint:

```http
POST {PINTO_API_URL}/v1/bots/webhook/receive
```

Request body:

```json
{
  "bot_id": "hermes_ai",
  "chat_id": "...",
  "reply_message": "Hello!"
}
```

If `PINTO_WEBHOOK_SECRET` is configured, the adapter also sends this header:

```http
X-Pinto-Secret: your-secret
```

---

## API Endpoints

| Environment | Base URL                        |
| ----------- | ------------------------------- |
| Production  | `https://api.pinto-app.com`     |
| Development | `https://api-dev.pinto-app.com` |

---

## File Structure

```text
hermes-pinto-adapter/
├── adapter.py
├── plugin.yaml
├── __init__.py
├── pinto_webhook_server.py
├── SKILL.md
├── .env.example
├── LICENSE
└── README.md
```

| File                      | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| `adapter.py`              | Main Hermes platform adapter                         |
| `plugin.yaml`             | Plugin metadata and environment variable definitions |
| `__init__.py`             | Python package init file                             |
| `pinto_webhook_server.py` | Standalone webhook test server                       |
| `SKILL.md`                | Hermes Skills install manifest                       |
| `.env.example`            | Environment variable example file                    |
| `LICENSE`                 | MIT License                                          |
| `README.md`               | Project documentation                                |

---

## Author

**Theeraphat S**
GitHub: [@Theeraphat-S](https://github.com/Theeraphat-S)

---

## License

MIT
