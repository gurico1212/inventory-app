#!/usr/bin/env python3
"""
料理レシピ要約アプリ
Claude API を使って料理レシピページを日本語で要約します。
"""

import os
import sys
import argparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import anthropic

load_dotenv()


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

    # スクリプト・スタイルなど不要なタグを除去
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "ads"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # 連続する空行を1行にまとめる
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def summarize_recipe(url: str) -> None:
    """レシピページを取得してClaudeで要約し、ストリーミング表示する"""
    print(f"ページを取得中: {url}\n")

    page_text = fetch_page(url)

    # テキストが長すぎる場合は先頭10,000文字に制限
    max_chars = 10_000
    if len(page_text) > max_chars:
        page_text = page_text[:max_chars] + "\n\n[... 以下省略 ...]"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = (
        "あなたは料理レシピの専門家です。"
        "ユーザーが提供するウェブページのテキストからレシピ情報を抽出し、"
        "以下の形式で分かりやすく日本語でまとめてください。\n\n"
        "# 料理名\n"
        "（料理名）\n\n"
        "## 材料\n"
        "- 材料1: 分量\n"
        "- 材料2: 分量\n"
        "...\n\n"
        "## 作り方\n"
        "1. 手順1\n"
        "2. 手順2\n"
        "...\n\n"
        "## ポイント・コツ\n"
        "（あれば記載）\n\n"
        "## 所要時間・難易度\n"
        "（あれば記載）\n\n"
        "レシピ情報がページに含まれていない場合はその旨を伝えてください。"
    )

    user_message = (
        f"以下のウェブページのテキストからレシピを要約してください。\n\n"
        f"URL: {url}\n\n"
        f"--- ページの内容 ---\n{page_text}\n--- ここまで ---"
    )

    print("Claude が要約を生成中...\n")
    print("=" * 60)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print("\n" + "=" * 60)
    final = stream.get_final_message()
    print(
        f"\n[使用トークン] 入力: {final.usage.input_tokens}, "
        f"出力: {final.usage.output_tokens}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="料理レシピページを Claude API で要約するツール"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="要約するレシピページのURL",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY が設定されていません。")
        print(".env ファイルに ANTHROPIC_API_KEY=your_api_key を記述してください。")
        sys.exit(1)

    url = args.url
    if not url:
        url = input("レシピページのURLを入力してください: ").strip()
        if not url:
            print("URLが入力されていません。")
            sys.exit(1)

    try:
        summarize_recipe(url)
    except requests.exceptions.RequestException as e:
        print(f"ページの取得に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIError as e:
        print(f"Claude API エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
