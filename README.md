# Crypto AI Assistant v1 Web Upload Edition

手機 GitHub 網頁上傳版。

## 先上傳這些檔案
- main.py
- requirements.txt
- services/
- core/
- telegram_bot/
- templates/
- github_workflows/

## GitHub Secrets 需要
- OPENAI_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## 重要
GitHub Actions 需要把：

github_workflows/daily_report.yml

移到：

.github/workflows/daily_report.yml

如果手機網頁不能上傳 .github 資料夾，就用 vscode.dev 建立：
.github/workflows/daily_report.yml
然後貼入 github_workflows/daily_report.yml 的內容。
