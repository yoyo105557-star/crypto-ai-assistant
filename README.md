# Crypto AI Assistant Single File Edition

只需要 3 個檔案：
- main.py
- requirements.txt
- daily_report.yml

## GitHub Secrets
- OPENAI_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## GitHub Actions
把 daily_report.yml 放到：
.github/workflows/daily_report.yml

如果手機 GitHub 不方便建立 .github 資料夾：
1. 先上傳 main.py / requirements.txt
2. 用 github.dev 建立 .github/workflows/daily_report.yml
3. 貼上 daily_report.yml 內容
