#!/usr/bin/env python3
"""Publish one standalone Threads post from the daily morning queue."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time as day_time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from publish_next import (
    create_threads_container,
    diagnose_threads_error,
    load_env,
    publish_threads_container,
    request_json,
    require_env,
    split_threads_text,
)


ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "content" / "threads-posts.json"
STATE_PATH = ROOT / "state" / "threads-state.json"
THREADS_TIMEZONE = "Europe/Moscow"
THREADS_PUBLISH_TIME = "09:00"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def morning_time() -> day_time:
    hour, minute = THREADS_PUBLISH_TIME.split(":", 1)
    return day_time(hour=int(hour), minute=int(minute))


def local_now(override: str | None) -> datetime:
    timezone = ZoneInfo(THREADS_TIMEZONE)
    if override:
        return datetime.fromisoformat(override).replace(tzinfo=timezone)
    return datetime.now(timezone)


def check_threads_config() -> None:
    token, user_id = require_env("THREADS_ACCESS_TOKEN", "THREADS_USER_ID")
    version = __import__("os").getenv("THREADS_API_VERSION", "v1.0")
    account = request_json(
        f"https://graph.threads.net/{version}/me",
        fields={"fields": "id,username", "access_token": token},
        method="GET",
    )
    if str(account.get("id")) != user_id:
        raise RuntimeError(
            "THREADS_USER_ID does not match the account returned by "
            "THREADS_ACCESS_TOKEN"
        )
    print(f"Threads account: @{account.get('username', user_id)}")
    print("Threads daily configuration check passed. Nothing was published.")


def publish_text_thread(post: dict[str, str]) -> None:
    token, user_id = require_env("THREADS_ACCESS_TOKEN", "THREADS_USER_ID")
    version = __import__("os").getenv("THREADS_API_VERSION", "v1.0")
    chunks = split_threads_text(post["text"])
    if not chunks:
        raise RuntimeError("Threads post text is empty")

    try:
        root_creation_id = create_threads_container(
            token, user_id, version, {"media_type": "TEXT", "text": chunks[0]}
        )
        root_post_id = publish_threads_container(
            token, user_id, version, root_creation_id
        )
        print("threads daily: root post sent")
        for chunk in chunks[1:]:
            reply_creation_id = create_threads_container(
                token,
                user_id,
                version,
                {"media_type": "TEXT", "text": chunk, "reply_to_id": root_post_id},
            )
            publish_threads_container(token, user_id, version, reply_creation_id)
            print("threads daily: reply sent")
    except Exception as exc:
        diagnose_threads_error(token, user_id, version, "daily text post", exc)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--date",
        help="Use an ISO datetime instead of now, e.g. 2026-09-06T09:05.",
    )
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()

    load_env()
    if args.check_config:
        check_threads_config()
        return 0

    posts: list[dict[str, str]] = load_json(POSTS_PATH, [])
    state: dict[str, Any] = load_json(STATE_PATH, {"next_index": 0, "published": {}})
    index = int(state.get("next_index", 0))
    if index >= len(posts):
        print("All daily Threads posts have already been published.")
        return 0

    now = local_now(args.date)
    today = now.date().isoformat()
    scheduled_at = datetime.combine(now.date(), morning_time()).replace(
        tzinfo=ZoneInfo(THREADS_TIMEZONE)
    )
    post = posts[index]
    print(f"Daily Threads post {index + 1}/{len(posts)}: {post['id']}")
    print(f"Date: {today}, scheduled: {scheduled_at.strftime('%Y-%m-%d %H:%M')} {THREADS_TIMEZONE}")
    print(post["text"])

    if not args.force:
        if now < scheduled_at:
            print("Nothing due yet.")
            return 0
        if state.get("last_publish_date") == today:
            print("Daily Threads post already sent today.")
            return 0
    if args.dry_run:
        print("Dry run: nothing sent.")
        return 0

    publish_text_thread(post)
    state.setdefault("published", {})[post["id"]] = today
    state["last_publish_date"] = today
    state["next_index"] = index + 1
    save_state(state)
    if state["next_index"] < len(posts):
        print(f"Advanced to daily Threads post {state['next_index'] + 1}.")
    else:
        print("Published the final daily Threads post.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
