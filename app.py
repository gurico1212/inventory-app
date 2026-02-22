#!/usr/bin/env python3
"""
料理レシピ要約 Web アプリ
Flask + Claude API (SSE ストリーミング) で iPhone でも使えるウェブアプリ
"""

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import anthropic
from flask import Flask, Response, render_template, request, stream_with_context

load_dotenv()

app = Flask(__name__)


def fetch_page(url: str) -> str:
    """URLからページのテキストコンテンツを取得する"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def generate_summary(url: str):
    """Claude API でレシピを要約し、SSE 形式でチャンクを yield する"""
    try:
        page_text = fetch_page(url)
    except requests.exceptions.RequestException as e:
        yield f"data: ERROR: ページの取得に失敗しました: {e}\n\n"
        return

    max_chars = 10_000
    if len(page_text) > max_chars:
        page_text = page_text[:max_chars] + "\n\n[... 以下省略 ...]"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = (
        "あなたは料理レシピの専門家です。"
        "ユーザーが提供するウェブページのテキストからレシピ情報を抽出し、"
        "以下の形式で分かりやすく日本語でまとめてください。\n\n"
        "# 料理名\n（料理名）\n\n"
        "## 材料\n- 材料1: 分量\n...\n\n"
        "## 作り方\n1. 手順1\n2. 手順2\n...\n\n"
        "## ポイント・コツ\n（あれば記載）\n\n"
        "## 所要時間・難易度\n（あれば記載）\n\n"
        "レシピ情報がページに含まれていない場合はその旨を伝えてください。"
    )

    user_message = (
        f"以下のウェブページのテキストからレシピを要約してください。\n\n"
        f"URL: {url}\n\n"
        f"--- ページの内容 ---\n{page_text}\n--- ここまで ---"
    )

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                # SSE 形式: data: <内容>\n\n
                # 改行はそのまま送れないのでエスケープして送る
                escaped = text.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"

        yield "data: [DONE]\n\n"
    except anthropic.APIError as e:
        yield f"data: ERROR: Claude API エラー: {e}\n\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/summarize")
def summarize():
    url = request.args.get("url", "").strip()
    if not url:
        return Response("data: ERROR: URLを入力してください\n\n", mimetype="text/event-stream")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return Response(
        stream_with_context(generate_summary(url)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が設定されていません。")
        print(".env ファイルに ANTHROPIC_API_KEY=your_api_key を記述してください。")
        exit(1)
    app.run(debug=False, host="0.0.0.0", port=5000)
