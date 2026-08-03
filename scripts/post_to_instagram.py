"""
queue/ フォルダにある写真を1枚選び、
1. Claude API で画像を見てキャプション+ハッシュタグを生成
2. GitHub raw URL 経由で Instagram Graph API に投稿
3. queue/ から posted/ へファイルを移動（コミットはワークフロー側で実施）

必要な環境変数（GitHub Secrets 経由で渡す）:
  ANTHROPIC_API_KEY       Claude APIキー
  IG_ACCESS_TOKEN         InstagramビジネスアカウントのGraph APIアクセストークン（長期）
  IG_BUSINESS_ACCOUNT_ID  InstagramビジネスアカウントのユーザーID
  GITHUB_REPOSITORY       "owner/repo" 形式（Actions内では自動で入る）
"""

import base64
import mimetypes
import os
import sys
import time
from pathlib import Path

import requests

QUEUE_DIR = Path("queue")
POSTED_DIR = Path("posted")
GRAPH_API_VERSION = "v21.0"

# ここをあなたの投稿スタイルに合わせて自由に調整してください。
CAPTION_SYSTEM_PROMPT = """あなたは風景・建築・自然・祭りを撮る写真家 さとしん(@sato44shin) の
Instagram投稿文を書くアシスタントです。

トーン: 誇張や過度な詩的表現は避け、撮影状況・被写体・光の状態など事実ベースの
描写を軸にする。押しつけがましいポエムにしない。
構成: 1〜3行程度の本文 + 空行 + 関連ハッシュタグ8〜15個。
ハッシュタグは日本語・英語を混ぜてよいが、スパムっぽい大量羅列は避ける。
出力は投稿本文のみ。前置きや説明は一切つけない。"""


def pick_next_photo() -> Path | None:
    candidates = sorted(
        p for p in QUEUE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )
    return candidates[0] if candidates else None


def generate_caption(photo_path: Path) -> str:
    image_bytes = photo_path.read_bytes()
    media_type = mimetypes.guess_type(photo_path.name)[0] or "image/jpeg"
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": 500,
            "system": CAPTION_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "この写真のInstagram投稿文を作ってください。",
                        },
                    ],
                }
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text").strip()


def public_image_url(photo_path: Path) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]  # "owner/repo"
    return f"https://raw.githubusercontent.com/{repo}/main/{photo_path.as_posix()}"


def post_to_instagram(image_url: str, caption: str) -> None:
    ig_user_id = os.environ["IG_BUSINESS_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}"

    # 1. メディアコンテナ作成
    create_resp = requests.post(
        f"{base}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=60,
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # 2. 画像取り込み完了を軽く待つ（通常は即time.sleep不要だが念のため）
    time.sleep(5)

    # 3. 公開
    publish_resp = requests.post(
        f"{base}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=60,
    )
    publish_resp.raise_for_status()


def main() -> int:
    photo = pick_next_photo()
    if photo is None:
        print("queue/ に投稿待ちの写真がありません。スキップします。")
        return 0

    print(f"投稿対象: {photo}")
    caption = generate_caption(photo)
    print(f"生成キャプション:\n{caption}")

    image_url = public_image_url(photo)
    post_to_instagram(image_url, caption)
    print("Instagramへの投稿が完了しました。")

    POSTED_DIR.mkdir(exist_ok=True)
    photo.rename(POSTED_DIR / photo.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
