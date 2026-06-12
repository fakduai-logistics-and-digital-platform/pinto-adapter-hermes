1|# 🫓 Hermes Pinto Chat Adapter
2|
3|**Pinto Chat** platform adapter plugin for [Hermes Agent](https://github.com/nousresearch/hermes-agent).
4|
5|Allows Hermes to act as a chatbot on [Pinto](https://pinto-app.com) — a Thai social platform. Receives webhook events from Pinto and replies via the Pinto Bot API.
6|
7|---
8|
9|## 🇹🇭 ภาษาไทย
10|
11|### คืออะไร?
12|
13|Plugin นี้ทำให้ Hermes Agent สามารถเป็นแชทบอทบนแอป Pinto ได้ รองรับทั้ง:
14|
15|- **Flat payload** (Production) — `message` เป็น string ธรรมดา
16|- **Nested payload** (Swagger spec) — `message` เป็น object ที่มี `content` และ `sender`
17|
18|### ติดตั้ง
19|
20|**วิธีที่ 1: ใช้ Hermes Skills (แนะนำ)**
21|
22|```bash
23|hermes skills install https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/SKILL.md
24|```
25|
26|**วิธีที่ 2: ติดตั้งเอง**
27|
28|```bash
29|# สร้างโฟลเดอร์ plugin
30|mkdir -p ~/.hermes/plugins/platforms/pinto
31|
32|# ดาวน์โหลดไฟล์
33|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
34|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
35|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py
36|
37|# ติดตั้ง dependencies
38|pip install httpx
39|```
40|
41|### ตั้งค่า
42|
43|เพิ่ม environment variables ใน `~/.hermes/.env`:
44|
45|```env
46|# จำเป็น
47|PINTO_BOT_ID=hermes_ai
48|
49|# ไม่จำเป็น
50|PINTO_API_URL=https://api.pinto-app.com
51|PINTO_WEBHOOK_SECRET=your-secret-key
52|PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
53|PINTO_HOME_CHANNEL=chat-id-for-cron
54|PINTO_ALLOWED_USERS=user-id-1,user-id-2
55|PINTO_ALLOW_ALL_USERS=true
56|```
57|
58|### ทดสอบแบบ Standalone (ไม่ต้องใช้ Hermes Gateway)
59|
60|```bash
61|# คัดลอก .env.example เป็น .env แล้วกรอกข้อมูล
62|cp .env.example .env
63|
64|# รันเซิร์ฟเวอร์
65|python pinto_webhook_server.py
66|
67|# หรือระบุ tunnel URL
68|python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
69|```
70|
71|---
72|
73|## 🇬🇧 English
74|
75|### What is this?
76|
77|This plugin lets Hermes Agent function as a chatbot on Pinto. It handles:
78|
79|- **Flat payload** (Production) — `message` is a plain string
80|- **Nested payload** (Swagger spec) — `message` is an object with `content` and `sender`
81|
82|### Install
83|
84|**Option 1: Hermes Skills (recommended)**
85|
86|```bash
87|hermes skills install https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/SKILL.md
88|```
89|
90|**Option 2: Manual install**
91|
92|```bash
93|# Create plugin directory
94|mkdir -p ~/.hermes/plugins/platforms/pinto
95|
96|# Download files
97|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/adapter.py -o ~/.hermes/plugins/platforms/pinto/adapter.py
98|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/plugin.yaml -o ~/.hermes/plugins/platforms/pinto/plugin.yaml
99|curl -sL https://raw.githubusercontent.com/fakduai-logistics-and-digital-platform/pinto-adapter-hermes/main/__init__.py -o ~/.hermes/plugins/platforms/pinto/__init__.py
100|
101|# Install dependencies
102|pip install httpx
103|```
104|
105|### Configure
106|
107|Add environment variables to `~/.hermes/.env`:
108|
109|```env
110|# Required
111|PINTO_BOT_ID=hermes_ai
112|
113|# Optional
114|PINTO_API_URL=https://api.pinto-app.com
115|PINTO_WEBHOOK_SECRET=your-secret-key
116|PINTO_WEBHOOK_PATH=/plugins/pinto/webhook
117|PINTO_HOME_CHANNEL=chat-id-for-cron
118|PINTO_ALLOWED_USERS=user-id-1,user-id-2
119|PINTO_ALLOW_ALL_USERS=true
120|```
121|
122|### Standalone Testing (no Hermes Gateway needed)
123|
124|```bash
125|# Copy .env.example to .env and fill in values
126|cp .env.example .env
127|
128|# Run the server
129|python pinto_webhook_server.py
130|
131|# Or specify a tunnel URL
132|python pinto_webhook_server.py --tunnel-url https://xxx.trycloudflare.com
133|```
134|
135|---
136|
137|## Webhook Payload Formats
138|
139|### Flat (Production)
140|
141|```json
142|{
143|  "user_id": "d5670660-df19-4c04-b042-c07c1005ae38",
144|  "username": "hermes",
145|  "message": "ไงhermes",
146|  "chat_id": "232d5b28-ba79-4ba8-98c9-6399dcb300e7",
147|  "bot_id": "hermes_ai"
148|}
149|```
150|
151|`message` is a **string** — not an object.
152|
153|### Nested (Swagger)
154|
155|```json
156|{
157|  "bot_id": "hermes_ai",
158|  "chat_id": "...",
159|  "message": {
160|    "chat_id": "...",
161|    "content": "Hello!",
162|    "sender": {
163|      "user_id": "...",
164|      "username": "user",
165|      "name": "User"
166|    }
167|  }
168|}
169|```
170|
171|---
172|
173|## Reply API
174|
175|Adapter sends replies via:
176|
177|```
178|POST {PINTO_API_URL}/v1/bots/webhook/receive
179|```
180|
181|Body:
182|
183|```json
184|{
185|  "bot_id": "hermes_ai",
186|  "chat_id": "...",
187|  "reply_message": "Hello!"
188|}
189|```
190|
191|Header (if secret configured): `X-Pinto-Secret: your-secret`
192|
193|---
194|
195|## File Structure
196|
197|```
198|hermes-pinto-adapter/
199|├── adapter.py              # Main platform adapter (Hermes plugin)
200|├── plugin.yaml             # Plugin metadata & env var definitions
201|├── __init__.py             # Python package init
202|├── pinto_webhook_server.py # Standalone test server
203|├── SKILL.md                # Hermes skills install manifest
204|├── .env.example            # Environment variable template
205|├── LICENSE                 # MIT License
206|└── README.md               # This file
207|```
208|
209|---
210|
211|## API Endpoints
212|
213|| Environment | Base URL |
214||---|---|
215|| Production | `https://api.pinto-app.com` |
216|| Development | `https://api-dev.pinto-app.com` |
217|
218|---
219|
220|## Author
221|
222|**Theeraphat S** ([@Theeraphat-S](https://github.com/Theeraphat-S))
223|
224|## License
225|
226|MIT
227|