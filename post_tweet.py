#!/usr/bin/env python3
"""
X (Twitter) 自動投稿スクリプト
AI副業系アカウント向け定時自動投稿システム
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import tweepy


# ─────────────────────────────────────────
# ログ設定
# ─────────────────────────────────────────
def setup_logger() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_filename = log_dir / f"tweet_{datetime.now().strftime('%Y%m')}.log"

    logger = logging.getLogger("tweet_poster")
    logger.setLevel(logging.INFO)

    # ファイルハンドラ（月別ログ）
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # コンソールハンドラ（GitHub Actions のログにも表示）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ─────────────────────────────────────────
# 環境変数からAPIキーを取得
# ─────────────────────────────────────────
def get_twitter_client() -> tweepy.Client:
    required_keys = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
        "TWITTER_BEARER_TOKEN",
    ]
    missing = [k for k in required_keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"環境変数が不足しています: {', '.join(missing)}")

    return tweepy.Client(
        bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


# ─────────────────────────────────────────
# posts.json の読み書き
# ─────────────────────────────────────────
POSTS_FILE = Path("posts.json")


def load_posts() -> list[dict]:
    if not POSTS_FILE.exists():
        raise FileNotFoundError(f"{POSTS_FILE} が見つかりません。")
    with POSTS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_posts(posts: list[dict]) -> None:
    with POSTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def get_next_unposted(posts: list[dict]) -> tuple[int, dict] | tuple[None, None]:
    """未投稿 (posted=false) の投稿を順番通りに1件返す"""
    for i, post in enumerate(posts):
        if not post.get("posted", False):
            return i, post
    return None, None


# ─────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────
def main() -> None:
    logger = setup_logger()
    logger.info("━━━ 自動投稿スクリプト 開始 ━━━")

    # posts.json 読み込み
    try:
        posts = load_posts()
        logger.info(f"投稿データ読み込み完了: {len(posts)} 件")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # 未投稿を取得
    idx, post = get_next_unposted(posts)
    if post is None:
        logger.info("未投稿の投稿がありません。全件投稿済みです。")
        sys.exit(0)

    tweet_text = post.get("text", "").strip()
    post_id = post.get("id", f"index_{idx}")

    if not tweet_text:
        logger.warning(f"投稿ID [{post_id}] のテキストが空です。スキップします。")
        posts[idx]["posted"] = True
        save_posts(posts)
        sys.exit(0)

    logger.info(f"投稿対象: ID={post_id}")
    logger.info(f"本文（先頭50字）: {tweet_text[:50]}...")

    # Xへ投稿
    try:
        client = get_twitter_client()
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        logger.info(f"✅ 投稿成功! Tweet ID: {tweet_id}")
        logger.info(f"   URL: https://x.com/i/web/status/{tweet_id}")
    except EnvironmentError as e:
        logger.error(f"環境変数エラー: {e}")
        sys.exit(1)
    except tweepy.TweepyException as e:
        logger.error(f"X API エラー: {e}")
        sys.exit(1)

    # posted フラグを更新
    posts[idx]["posted"] = True
    posts[idx]["posted_at"] = datetime.now().isoformat()
    posts[idx]["tweet_id"] = tweet_id
    save_posts(posts)
    logger.info(f"posts.json を更新しました (posted=true, index={idx})")
    logger.info("━━━ 自動投稿スクリプト 完了 ━━━")


if __name__ == "__main__":
    main()
