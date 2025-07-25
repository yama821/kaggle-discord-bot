from kaggle.api.kaggle_api_extended import KaggleApi
from datetime import datetime
import time
import pandas as pd
import os
import requests  # pip install requests
import json

STATUS_COLORS = {          # 好みで調整
    "PENDING":   0xFFC107, # 黄
    "RUNNING":   0x3498DB, # 青
    "COMPLETE":  0x2ECC71, # 緑
    "FAILED":    0xE74C3C, # 赤
}

class DiscordWebhookClient:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def post(self, payload):
        resp = requests.post(
            self.webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        print("sent:", resp.status_code)

def result_to_embed(sub: dict, base="https://www.kaggle.com"):
    """Kaggle API 辞書 → DiscordEmbed へ変換"""
    status = sub.get("status", "UNKNOWN")
    color  = STATUS_COLORS.get(status, 0x95A5A6)  # デフォ灰色

    embed = {
        "title": f"新しい提出 (by {sub['submittedByRef']})",
        "url": f"{base}{sub['url']}",
        "color": color,
        "timestamp": str(sub["date_jst"])
    }

    dt = datetime.now(sub["date_jst"].tzinfo) - sub["date_jst"]
    if status == "COMPLETE":
        embed["title"] = "採点完了"
        embed["fields"] = [
            {"name": "score", "value": sub['publicScore']},
            {"name": "time", "value": str(dt)},
        ]

    # === 本文（空なら入れない） ===
    if sub.get("description"):
        embed["description"] = sub["description"]


    return embed


def main():
    api = KaggleApi()
    api.authenticate()

    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    client = DiscordWebhookClient(webhook_url)

    competition =  'cmi-detect-behavior-with-sensor-data'
    # competition = input()

    pending_refs = set()
    while True:
        results = api.competition_submissions(competition)

        results = [result.to_dict() for result in results]
        df = pd.DataFrame(results)

        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["date_jst"] = df["date"].dt.tz_convert("Asia/Tokyo")

        for _, row in df.iterrows():
            ref = row['ref']
            status = row['status']
            # print(row)
            # print(type(status))
            # print(status)
            print(status)
            if status != 'COMPLETE' and ref not in pending_refs:
                print(f"{ref=}")
                pending_refs.add(ref)
                emb = result_to_embed(row.to_dict())
                payload = {
                    "embeds": [emb]
                }
                client.post(payload)

            if status == 'COMPLETE' and ref in pending_refs:
                pending_refs.remove(ref)
                emb = result_to_embed(row.to_dict())
                payload = {
                    "embeds": [emb]
                }
                client.post(payload)

        time.sleep(60)


if __name__ == "__main__":
    main()
