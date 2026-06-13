#!/usr/bin/env python3
"""Publish and remove a technical 4:5 image without touching the content queue."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_next as app


STATE_PATH = app.ROOT / "state" / "test-social-formats.json"
IMAGE_PATH = app.ROOT / "assets" / "test" / "format-check.jpg"
CAPTION = (
    "ТЕСТ ФОРМАТА 4:5\n\n"
    "Проверяем отображение изображения в ленте. "
    "Пост будет удален после проверки.\n\n"
    "#правдажизни"
)


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def wait_for_postmypost_file(upload_id: int) -> int:
    for _ in range(30):
        status = app.request_postmypost(
            "upload/status", query={"id": str(upload_id)}
        )
        if int(status["status"]) == 1 and status.get("file_id"):
            return int(status["file_id"])
        if int(status["status"]) == 2:
            raise RuntimeError("Postmypost could not process the test image")
        time.sleep(2)
    raise RuntimeError("Timed out while Postmypost processed the test image")


def publish() -> None:
    if STATE_PATH.exists():
        raise RuntimeError(
            "A format test already exists. Delete it before publishing another."
        )
    if not IMAGE_PATH.exists():
        raise RuntimeError(f"Test image not found: {IMAGE_PATH}")
    state: dict = {"created_at": datetime.now().astimezone().isoformat()}
    telegram_token, telegram_chat = app.require_env(
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"
    )
    telegram = app.request_json(
        f"https://api.telegram.org/bot{telegram_token}/sendPhoto",
        fields={"chat_id": telegram_chat, "caption": CAPTION},
        files={"photo": IMAGE_PATH},
    )
    state["telegram"] = {
        "chat_id": telegram_chat,
        "message_id": telegram["result"]["message_id"],
    }
    save_state(state)
    print("telegram_test=published")

    project_id, account_id, account_name = app.discover_postmypost_vk()
    image_url = app.upload_public_image(IMAGE_PATH)
    upload = app.request_postmypost(
        "upload/init",
        method="POST",
        payload={"project_id": project_id, "url": image_url},
    )
    file_id = wait_for_postmypost_file(int(upload["id"]))
    publication = app.request_postmypost(
        "publications",
        method="POST",
        payload={
            "project_id": project_id,
            "post_at": (
                datetime.now().astimezone() + timedelta(minutes=2)
            ).isoformat(timespec="seconds"),
            "account_ids": [account_id],
            "publication_status": 5,
            "details": [
                {
                    "account_id": account_id,
                    "publication_type": 1,
                    "content": CAPTION,
                    "file_ids": [file_id],
                }
            ],
        },
    )
    state["vk"] = {
        "project_id": project_id,
        "account_id": account_id,
        "account_name": account_name,
        "publication_id": publication["id"],
    }
    save_state(state)
    print("vk_test=created")

    instagram_token, instagram_user = app.require_env(
        "IG_ACCESS_TOKEN", "IG_USER_ID"
    )
    instagram_version = app.os.getenv("IG_API_VERSION", "v25.0")
    image_url = app.upload_public_image(IMAGE_PATH)
    creation = app.request_json(
        app.meta_url("graph.instagram.com", instagram_version, f"{instagram_user}/media"),
        fields={
            "image_url": image_url,
            "caption": CAPTION,
            "access_token": instagram_token,
        },
    )
    published = app.request_json(
        app.meta_url(
            "graph.instagram.com", instagram_version, f"{instagram_user}/media_publish"
        ),
        fields={"creation_id": creation["id"], "access_token": instagram_token},
    )
    state["instagram"] = {"media_id": published["id"]}
    save_state(state)
    print("instagram_test=published")
    print(f"test_state={STATE_PATH}")


def delete() -> None:
    state = app.load_json(STATE_PATH, {})
    if not state:
        raise RuntimeError("No format test state found")
    if telegram := state.get("telegram"):
        telegram_token, = app.require_env("TELEGRAM_BOT_TOKEN")
        app.request_json(
            f"https://api.telegram.org/bot{telegram_token}/deleteMessage",
            fields={
                "chat_id": str(telegram["chat_id"]),
                "message_id": str(telegram["message_id"]),
            },
        )
        print("telegram_test=deleted")
    if vk := state.get("vk"):
        try:
            app.request_postmypost(
                f"publications/{vk['publication_id']}",
                method="DELETE",
                query={
                    "delete_option": "1",
                    "account_ids": str(vk["account_id"]),
                },
            )
        except urllib.error.HTTPError as exc:
            # Postmypost currently returns HTTP 422 after a successful delete
            # because its empty response fails the service's own schema check.
            if exc.code != 422:
                raise
        print("vk_test=delete_requested")
    print("instagram_test=delete_manually_in_the_instagram_app")
    STATE_PATH.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("publish", "delete"))
    args = parser.parse_args()
    app.load_env()
    if args.action == "publish":
        publish()
    else:
        delete()


if __name__ == "__main__":
    main()
