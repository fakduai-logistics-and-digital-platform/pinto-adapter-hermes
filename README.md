# 🫓 Hermes Pinto Chat Adapter

**Pinto Chat** platform adapter plugin for [Hermes Agent](https://github.com/nousresearch/hermes-agent).

Allows Hermes to act as a chatbot on [Pinto](https://pinto-app.com) — a Thai social platform. Receives webhook events from Pinto and replies via the Pinto Bot API.

---

## 🇹🇭 ภาษาไทย

### คืออะไร?

Plugin นี้ทำให้ Hermes Agent สามารถเป็นแชทบอทบนแอป Pinto ได้ รองรับทั้ง:

- **Flat payload** (Production) — `message` เป็น string ธรรมดา
- **Nested payload** (Swagger spec) — `message` เป็น object ที่มี `content` และ `sender`

### ติดตั้ง

**วิธีที่ 1: ใช้ Hermes Skills (แนะนำ)**

```bash
hermes skills install https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/SKILL.md
```

**วิธีที่ 2: ติดตั้งเอง**

```bash
# สร้างโฟลเดอร์ plugin
mkdir -p ~/.hermes/plugins/platforms/pinto

# ดาวน์โหลดไฟล์
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py

# ติดตั้ง dependencies
pip install httpx
```

### ตั้งค่า

เพิ่ม environment variables ใน `~/.hermes/.env`:

```env
# จำเป็น
PINTO_BOT_ID=hermes_ai

# ไม่จำเป็น
PINTO_API_URL=https://api.pinto-app.com
PINTO_WEBHOOK_SECRET=your-secret-key
PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
PINTO_HOME_CHANNEL=chat-id-for-cron
PINTO_ALLOWED_USERS=user-id-1,user-id-2
PINTO_ALLOW_ALL_USERS=true
```

### ทดสอบแบบ Standalone (ไม่ต้องใช้ Hermes Gateway)

```bash
# คัดลอก .env.example เป็น .env แล้วกรอกข้อมูล
cp .env.example .env

# รันเซิร์ฟเวอร์
python pinto_webhook_server.py

# หรือระบุ tunnel URL
python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
```

---

## 🇬🇧 English

### What is this?

This plugin lets Hermes Agent function as a chatbot on Pinto. It handles:

- **Flat payload** (Production) — `message` is a plain string
- **Nested payload** (Swagger spec) — `message` is an object with `content` and `sender`

### Install

**Option 1: Hermes Skills (recommended)**

```bash
hermes skills install https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/SKILL.md
```

**Option 2: Manual install**

```bash
# Create plugin directory
mkdir -p ~/.hermes/plugins/platforms/pinto

# Download files
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
curl -sL https://raw.githubusercontent.com/Theeraphat-S/hermes-pinto-adapter/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py

# Install dependencies
pip install httpx
```

### Configure

Add environment variables to `~/.hermes/.env`:

```env
# Required
PINTO_BOT_ID=hermes_ai

# Optional
PINTO_API_URL=https://api.pinto-app.com
PINTO_WEBHOOK_SECRET=your-secret-key
PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
PINTO_HOME_CHANNEL=chat-id-for-cron
PINTO_ALLOWED_USERS=user-id-1,user-id-2
PINTO_ALLOW_ALL_USERS=true
```

### Standalone Testing (no Hermes Gateway needed)

```bash
# Copy .env.example to .env and fill in values
cp .env.example .env

# Run the server
python pinto_webhook_server.py

# Or specify a tunnel URL
python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
```

---

## Webhook Payload Formats

### Flat (Production)

```json
{
  "user_id": "d5670660-df19-4c04-b042-c07c1005ae38",
  "username": "hermes",
  "message": "ไงhermes",
  "chat_id": "232d5b28-ba79-4ba8-98c9-6399dcb300e7",
  "bot_id": "hermes_ai"
}
```

`message` is a **string** — not an object.

### Nested (Swagger)

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

---

## Reply API

Adapter sends replies via:

```
POST {PINTO_API_URL}/v1/bots/webhook/receive
```

Body:

```json
{
  "bot_id": "hermes_ai",
  "chat_id": "...",
  "reply_message": "Hello!"
}
```

Header (if secret configured): `X-Pinto-Secret: your-secret`

---

## File Structure

```
hermes-pinto-adapter/
├── adapter.py              # Main platform adapter (Hermes plugin)
├── plugin.yaml             # Plugin metadata & env var definitions
├── __init__.py             # Python package init
├── pinto_webhook_server.py # Standalone test server
├── SKILL.md                # Hermes skills install manifest
├── .env.example            # Environment variable template
├── LICENSE                 # MIT License
└── README.md               # This file
```

---

## API Endpoints

| Environment | Base URL |
|---|---|
| Production | `https://api.pinto-app.com` |
| Development | `https://api-dev.pinto-app.com` |

---

## Author

**Theeraphat S** ([@Theeraphat-S](https://github.com/Theeraphat-S))

## License

MIT
