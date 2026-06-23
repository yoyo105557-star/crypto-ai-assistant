import os
from openai import OpenAI
from services.market_data import fetch_all
from core.score import build_scores
from core.report import build_report
from telegram_bot.sender import send_telegram_message

SYSTEM_PROMPT = """你是使用者的加密貨幣交易助理。請根據資料提供簡短中文交易晨報補充。
要求：
1. 不要保證獲利。
2. 不要叫使用者高槓桿。
3. 強調等待流動性掃蕩與成交量確認。
4. 如果資料不足，明確說資料不足。
5. 回答控制在120字內。
"""

def ai_comment(raw_report):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "OpenAI API Key 未設定，僅輸出系統量化報告。"
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_report}
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 分析失敗：{e}"

def main():
    data = fetch_all()
    scores = build_scores(data)
    draft = build_report(data, scores)
    comment = ai_comment(draft)
    final_report = build_report(data, scores, comment)
    send_telegram_message(final_report)
    print("Report sent.")

if __name__ == "__main__":
    main()
