#!/usr/bin/env python3
"""Publish the next prepared Back2Life post to configured social platforms."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, time as day_time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "content" / "posts.json"
CALENDAR_PATH = ROOT / "content" / "publishing-calendar.json"
STATE_PATH = ROOT / "state" / "publisher-state.json"
ENV_PATH = ROOT / ".env"
TITLE_FONT_SIZE = 76
TITLE_TEXT_COLOR = (246, 239, 229, 255)
TITLE_BOX_COLOR = (13, 29, 36, 184)
TITLE_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
)


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_content() -> tuple[list[dict[str, str]], list[date], bool]:
    posts: list[dict[str, str]] = load_json(POSTS_PATH, [])
    calendar: dict[str, Any] = load_json(CALENDAR_PATH, {})
    dates = [date.fromisoformat(value) for value in calendar.get("dates", [])]
    sheet_url = os.getenv("CONTENT_SHEET_CSV_URL")
    if not sheet_url:
        return posts, dates, False
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(sheet_url, timeout=30) as response:
                rows = list(
                    csv.reader(io.StringIO(response.read().decode("utf-8-sig")))
                )
            break
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < 3:
                print(
                    "WARNING: Could not fetch CONTENT_SHEET_CSV_URL, "
                    f"retrying ({attempt}/3): {exc}",
                    file=sys.stderr,
                )
                time.sleep(5)
    else:
        raise RuntimeError(
            "Could not fetch CONTENT_SHEET_CSV_URL after 3 attempts"
        ) from last_error
    content_rows = [
        row for row in rows[1:] if any(value.strip() for value in row[:3])
    ]
    if len(content_rows) != len(posts):
        raise RuntimeError(
            f"Expected {len(posts)} content rows in the Codex sheet, "
            f"found {len(content_rows)}"
        )
    sheet_posts: list[dict[str, str]] = []
    sheet_dates: list[date] = []
    for index, row in enumerate(content_rows):
        if len(row) < 3 or not all(value.strip() for value in row[:3]):
            raise RuntimeError(f"Incomplete Codex sheet row: {index + 2}")
        sheet_dates.append(date.fromisoformat(row[0].strip()))
        sheet_posts.append(
            {
                **posts[index],
                "title": row[1].strip(),
                "text": row[2].strip(),
            }
        )
    return sheet_posts, sheet_dates, True


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def publication_time(calendar: dict[str, Any]) -> day_time:
    value = str(calendar.get("publish_time", "19:00"))
    hour, minute = value.split(":", 1)
    return day_time(hour=int(hour), minute=int(minute))


def local_now(calendar: dict[str, Any], override: str | None) -> datetime:
    timezone = ZoneInfo(calendar.get("timezone", "Europe/Moscow"))
    if override:
        day = date.fromisoformat(override)
        return datetime.combine(day, publication_time(calendar)).replace(
            tzinfo=timezone
        )
    return datetime.now(timezone)


def scheduled_datetime(day: date, calendar: dict[str, Any]) -> datetime:
    timezone = ZoneInfo(calendar.get("timezone", "Europe/Moscow"))
    return datetime.combine(day, publication_time(calendar)).replace(
        tzinfo=timezone
    )


def local_date(calendar: dict[str, Any], override: str | None) -> date:
    if override:
        return date.fromisoformat(override)
    timezone = ZoneInfo(calendar.get("timezone", "Europe/Moscow"))
    return datetime.now(timezone).date()


def is_blocked(day: date, calendar: dict[str, Any]) -> bool:
    rules = calendar.get("rules", {})
    if rules.get("skip_sundays") and day.weekday() == 6:
        return True
    if rules.get("skip_last_day_of_month"):
        tomorrow = date.fromordinal(day.toordinal() + 1)
        if tomorrow.month != day.month:
            return True
    if day.isoformat() in rules.get("extra_blocked_dates", []):
        return True
    anchor_value = rules.get("biweekly_monday_announcement_anchor")
    if anchor_value and day.weekday() == 0:
        anchor = date.fromisoformat(anchor_value)
        if (day - anchor).days % 14 == 0:
            return True
    return False


def multipart_body(
    fields: dict[str, str], files: dict[str, Path]
) -> tuple[bytes, str]:
    boundary = f"----Back2Life{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for key, path in files.items():
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{key}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def request_json(
    url: str,
    *,
    fields: dict[str, str] | None = None,
    files: dict[str, Path] | None = None,
    method: str = "POST",
) -> dict[str, Any]:
    if files:
        data, content_type = multipart_body(fields or {}, files)
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": content_type}, method=method
        )
    elif method == "GET":
        query = urllib.parse.urlencode(fields or {})
        separator = "&" if "?" in url else "?"
        request = urllib.request.Request(
            f"{url}{separator}{query}" if query else url, method=method
        )
    else:
        data = urllib.parse.urlencode(fields or {}).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("ok") is False or "error" in payload:
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    return payload


def request_postmypost(
    resource: str,
    *,
    query: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    method: str = "GET",
) -> dict[str, Any]:
    token, = require_env("POSTMYPOST_ACCESS_TOKEN")
    base = os.getenv("POSTMYPOST_API_BASE", "https://api.postmypost.io/v4.1")
    url = f"{base.rstrip('/')}/{resource.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def require_env(*names: str) -> list[str]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    return [os.environ[name] for name in names]


def enabled_platforms() -> tuple[str, ...]:
    supported = ("telegram", "vk", "instagram", "facebook")
    value = os.getenv("ENABLED_PLATFORMS", "telegram,vk,instagram")
    requested = tuple(
        platform.strip() for platform in value.split(",") if platform.strip()
    )
    invalid = [platform for platform in requested if platform not in supported]
    if invalid:
        raise RuntimeError(f"Unsupported platforms: {', '.join(invalid)}")
    if not requested:
        raise RuntimeError("ENABLED_PLATFORMS cannot be empty")
    return requested


def publish_telegram(post: dict[str, str], image_path: Path | None) -> None:
    token, chat_id = require_env("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    base = f"https://api.telegram.org/bot{token}"
    message = f"<b>{html.escape(post['title'])}</b>\n\n{html.escape(post['text'])}"
    plain_length = len(f"{post['title']}\n\n{post['text']}")
    if plain_length > 4096:
        raise RuntimeError(
            f"Telegram post is too long for one message: {plain_length} characters"
        )
    if image_path is None:
        request_json(
            f"{base}/sendMessage",
            fields={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        )
        return
    image_path = titled_image_path("telegram", image_path, post["title"])
    if not image_path.exists():
        raise RuntimeError(f"Telegram JPEG not found: {image_path}")
    image_url = upload_public_image(image_path)
    request_json(
        f"{base}/sendMessage",
        fields={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "link_preview_options": json.dumps(
                {
                    "url": image_url,
                    "prefer_large_media": True,
                    "show_above_text": True,
                }
            ),
        },
    )


def vk_token_env(use_user_token: bool = False) -> str:
    if use_user_token and os.getenv("VK_USER_ACCESS_TOKEN"):
        return "VK_USER_ACCESS_TOKEN"
    return "VK_ACCESS_TOKEN"


def vk_api(
    method: str, fields: dict[str, str], *, use_user_token: bool = False
) -> Any:
    token, = require_env(vk_token_env(use_user_token))
    payload = request_json(
        f"https://api.vk.com/method/{method}",
        fields={
            **fields,
            "access_token": token,
            "v": os.getenv("VK_API_VERSION", "5.199"),
        },
    )
    return payload.get("response", payload)


def resolve_vk_group_id() -> int:
    raw_group_id, = require_env("VK_GROUP_ID")
    value = raw_group_id.strip().lstrip("@")
    for prefix in ("club", "public"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.startswith("-"):
        value = value[1:]
    if value.isdigit():
        return int(value)
    resolved = vk_api("utils.resolveScreenName", {"screen_name": value})
    if not resolved or resolved.get("type") != "group":
        raise RuntimeError(f"VK_GROUP_ID is not a VK community: {raw_group_id}")
    return int(resolved["object_id"])


def publish_vk_direct(post: dict[str, str], image_path: Path | None) -> None:
    group_id = resolve_vk_group_id()
    use_user_token = bool(os.getenv("VK_USER_ACCESS_TOKEN"))
    if image_path is not None and not use_user_token:
        raise RuntimeError(
            "VK image publishing requires VK_USER_ACCESS_TOKEN. "
            "Community tokens cannot upload wall photos."
        )
    message = f"{post['title']}\n\n{post['text']}"
    fields = {
        "owner_id": f"-{group_id}",
        "from_group": "1",
        "message": message,
        "guid": f"back2life-{post['id']}",
    }
    if image_path is not None:
        image_path = titled_image_path("telegram", image_path, post["title"])
        upload_server = vk_api(
            "photos.getWallUploadServer",
            {"group_id": str(group_id)},
            use_user_token=use_user_token,
        )
        uploaded = request_json(
            upload_server["upload_url"], files={"photo": image_path}
        )
        saved = vk_api(
            "photos.saveWallPhoto",
            {
                "group_id": str(group_id),
                "photo": uploaded["photo"],
                "server": str(uploaded["server"]),
                "hash": uploaded["hash"],
            },
            use_user_token=use_user_token,
        )
        photo = saved[0]
        fields["attachments"] = f"photo{photo['owner_id']}_{photo['id']}"
    vk_api("wall.post", fields, use_user_token=use_user_token)


def discover_postmypost_vk() -> tuple[int, int, str]:
    project_override = os.getenv("POSTMYPOST_PROJECT_ID")
    account_override = os.getenv("POSTMYPOST_VK_ACCOUNT_ID")
    if project_override and account_override:
        accounts = request_postmypost(
            "accounts", query={"project_id": project_override}
        ).get("data", [])
        for account in accounts:
            if int(account["id"]) == int(account_override):
                if int(account.get("connection_status", 0)) != 1:
                    raise RuntimeError("The configured Postmypost VK account is disconnected")
                return int(project_override), int(account_override), account["name"]
        raise RuntimeError("The configured Postmypost VK account was not found")
    channels = request_postmypost("channels").get("data", [])
    vk_channel_ids = {
        int(channel["id"])
        for channel in channels
        if any(
            marker in f"{channel.get('code', '')} {channel.get('name', '')}".lower()
            for marker in ("vk", "vkontakte", "вконтакте")
        )
    }
    if not vk_channel_ids:
        raise RuntimeError("Postmypost did not return a VK channel")
    matches: list[tuple[int, int, str]] = []
    for project in request_postmypost("projects").get("data", []):
        project_id = int(project["id"])
        if project_override and project_id != int(project_override):
            continue
        accounts = request_postmypost(
            "accounts", query={"project_id": str(project_id)}
        ).get("data", [])
        for account in accounts:
            account_id = int(account["id"])
            if account_override and account_id != int(account_override):
                continue
            if (
                int(account.get("chanel_id", 0)) in vk_channel_ids
                and int(account.get("connection_status", 0)) == 1
            ):
                matches.append((project_id, account_id, account["name"]))
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one connected VK account in Postmypost. "
            "Set POSTMYPOST_PROJECT_ID and POSTMYPOST_VK_ACCOUNT_ID if needed."
        )
    return matches[0]


def publish_vk(post: dict[str, str], image_path: Path | None) -> None:
    direct_error: Exception | None = None
    if os.getenv("VK_ACCESS_TOKEN") and os.getenv("VK_GROUP_ID"):
        try:
            publish_vk_direct(post, image_path)
            return
        except Exception as exc:
            direct_error = exc
            print(f"vk direct publish failed, trying Postmypost: {exc}", file=sys.stderr)
    try:
        project_id, account_id, _ = discover_postmypost_vk()
        detail: dict[str, Any] = {
            "account_id": account_id,
            "publication_type": 1,
            "content": f"{post['title']}\n\n{post['text']}",
        }
        if image_path is not None:
            image_path = titled_image_path("telegram", image_path, post["title"])
            image_url = upload_public_image(image_path)
            upload = request_postmypost(
                "upload/init",
                method="POST",
                payload={"project_id": project_id, "url": image_url},
            )
            for _ in range(30):
                upload_status = request_postmypost(
                    "upload/status", query={"id": str(upload["id"])}
                )
                if int(upload_status["status"]) == 1 and upload_status.get("file_id"):
                    break
                if int(upload_status["status"]) == 2:
                    raise RuntimeError("Postmypost could not process the VK image")
                time.sleep(2)
            else:
                raise RuntimeError("Timed out while Postmypost processed the VK image")
            detail["file_ids"] = [int(upload_status["file_id"])]
        now = (datetime.now().astimezone() + timedelta(minutes=2)).isoformat(
            timespec="seconds"
        )
        request_postmypost(
            "publications",
            method="POST",
            payload={
                "project_id": project_id,
                "post_at": now,
                "account_ids": [account_id],
                "publication_status": 5,
                "details": [detail],
            },
        )
    except Exception as exc:
        if direct_error is not None:
            raise RuntimeError(
                f"VK direct failed: {direct_error}; Postmypost failed: {exc}"
            ) from exc
        raise


def meta_url(host: str, version: str, resource: str) -> str:
    return f"https://{host}/{version}/{resource}"


def instagram_image_path(image_path: Path) -> Path:
    return ROOT / "assets" / "instagram" / f"{image_path.stem}.jpg"


def telegram_image_path(image_path: Path) -> Path:
    return ROOT / "assets" / "telegram" / f"{image_path.stem}.jpg"


def platform_image_path(platform: str, image_path: Path) -> Path:
    if platform == "instagram":
        return instagram_image_path(image_path)
    if platform in {"telegram", "vk"}:
        return telegram_image_path(image_path)
    if platform == "facebook":
        return instagram_image_path(image_path)
    raise RuntimeError(f"Unsupported image platform: {platform}")


def title_font_path() -> str:
    configured = os.getenv("TITLE_FONT_PATH")
    candidates = (configured,) + TITLE_FONT_CANDIDATES if configured else TITLE_FONT_CANDIDATES
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "Could not find a title font. Set TITLE_FONT_PATH to a TrueType font file."
    )


def text_width(draw: Any, text: str, font: Any) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return int(right - left)


def wrap_title(draw: Any, title: str, font: Any, max_width: int) -> list[str]:
    words = title.split()
    if not words:
        return [title]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def titled_image_path(platform: str, image_path: Path, title: str) -> Path:
    source_path = platform_image_path(platform, image_path)
    if not source_path.exists():
        raise RuntimeError(f"{platform.capitalize()} JPEG not found: {source_path}")

    font_path = title_font_path()
    digest = hashlib.sha1(
        "\0".join(
            (
                platform,
                str(source_path),
                str(source_path.stat().st_size),
                str(source_path.stat().st_mtime_ns),
                title,
                str(TITLE_FONT_SIZE),
                repr(TITLE_TEXT_COLOR),
                repr(TITLE_BOX_COLOR),
                font_path,
            )
        ).encode("utf-8")
    ).hexdigest()[:12]
    output_path = (
        ROOT
        / "tmp"
        / "titled-images"
        / platform
        / f"{source_path.stem}-{digest}.jpg"
    )
    if output_path.exists():
        return output_path

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required to render titles on post images. "
            "Install dependencies with: python3 -m pip install -r requirements.txt"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as image:
        canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(font_path, TITLE_FONT_SIZE)

    width, height = canvas.size
    margin_x = 64
    margin_bottom = 76
    padding_x = 36
    padding_y = 28
    line_gap = 12
    max_text_width = width - (margin_x * 2) - (padding_x * 2)
    lines = wrap_title(draw, title, font, max_text_width)
    line_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_widths = [right - left for left, _, right, _ in line_boxes]
    line_heights = [bottom - top for _, top, _, bottom in line_boxes]
    text_width_px = int(max(line_widths) if line_widths else 0)
    text_height_px = int(sum(line_heights) + line_gap * (len(lines) - 1))

    box_left = margin_x
    box_bottom = height - margin_bottom
    box_right = min(width - margin_x, box_left + text_width_px + padding_x * 2)
    box_top = box_bottom - text_height_px - padding_y * 2
    draw.rounded_rectangle(
        (box_left, box_top, box_right, box_bottom),
        radius=30,
        fill=TITLE_BOX_COLOR,
    )

    text_x = box_left + padding_x
    text_y = box_top + padding_y
    for index, line in enumerate(lines):
        left, top, _, bottom = line_boxes[index]
        draw.text(
            (text_x - left, text_y - top),
            line,
            font=font,
            fill=TITLE_TEXT_COLOR,
            stroke_width=1,
            stroke_fill=(5, 15, 18, 180),
        )
        text_y += (bottom - top) + line_gap

    titled = Image.alpha_composite(canvas, overlay).convert("RGB")
    titled.save(output_path, format="JPEG", quality=92, optimize=True)
    return output_path


def cloudinary_signature(fields: dict[str, str], secret: str) -> str:
    serialized = "&".join(
        f"{key}={value}" for key, value in sorted(fields.items()) if value
    )
    return hashlib.sha1(f"{serialized}{secret}".encode("utf-8")).hexdigest()


def upload_public_image(image_path: Path) -> str:
    cloud, api_key, api_secret = require_env(
        "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"
    )
    timestamp = str(int(datetime.now().timestamp()))
    variant = image_path.parent.name
    if variant in {"instagram", "telegram", "posts"}:
        public_id = f"back2life/{variant}/{image_path.stem}"
    else:
        public_id = f"back2life/{image_path.stem}"
    signed_fields = {
        "overwrite": "true",
        "public_id": public_id,
        "timestamp": timestamp,
    }
    upload = request_json(
        f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
        fields={
            **signed_fields,
            "api_key": api_key,
            "signature": cloudinary_signature(signed_fields, api_secret),
            "overwrite": "true",
        },
        files={"file": image_path},
    )
    return upload["secure_url"]


def instagram_post_exists(
    token: str, user_id: str, version: str, title: str
) -> bool:
    media = request_json(
        meta_url("graph.instagram.com", version, f"{user_id}/media"),
        fields={
            "fields": "id,caption,timestamp",
            "limit": "5",
            "access_token": token,
        },
        method="GET",
    )
    for item in media.get("data", []):
        caption = item.get("caption") or ""
        if caption.strip().startswith(title):
            return True
    return False


def publish_instagram(post: dict[str, str], image_path: Path | None) -> None:
    if image_path is None:
        print("instagram: text-only post skipped because Instagram requires media")
        return
    token, user_id = require_env("IG_ACCESS_TOKEN", "IG_USER_ID")
    version = os.getenv("IG_API_VERSION", "v25.0")
    jpeg_path = titled_image_path("instagram", image_path, post["title"])
    if not jpeg_path.exists():
        raise RuntimeError(f"Instagram JPEG not found: {jpeg_path}")
    image_url = upload_public_image(jpeg_path)
    creation = request_json(
        meta_url("graph.instagram.com", version, f"{user_id}/media"),
        fields={
            "image_url": image_url,
            "caption": f"{post['title']}\n\n{post['text']}",
            "access_token": token,
        },
    )
    try:
        request_json(
            meta_url("graph.instagram.com", version, f"{user_id}/media_publish"),
            fields={"creation_id": creation["id"], "access_token": token},
        )
    except Exception:
        if instagram_post_exists(token, user_id, version, post["title"]):
            print("instagram: post is already visible after publish error")
            return
        raise


def publish_facebook(post: dict[str, str], image_path: Path | None) -> None:
    if image_path is None:
        print("facebook: text-only post skipped because Facebook image support is disabled")
        return
    token, page_id = require_env("FB_PAGE_ACCESS_TOKEN", "FB_PAGE_ID")
    version = os.getenv("FB_GRAPH_API_VERSION", "v25.0")
    image_path = titled_image_path("facebook", image_path, post["title"])
    request_json(
        meta_url("graph.facebook.com", version, f"{page_id}/photos"),
        fields={
            "message": f"{post['title']}\n\n{post['text']}",
            "access_token": token,
        },
        files={"source": image_path},
    )


def check_config() -> None:
    targets = enabled_platforms()
    if "telegram" in targets:
        telegram_token, chat_id = require_env(
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"
        )
        telegram_base = f"https://api.telegram.org/bot{telegram_token}"
        bot = request_json(f"{telegram_base}/getMe")["result"]
        chat = request_json(
            f"{telegram_base}/getChat", fields={"chat_id": chat_id}
        )["result"]
        print(f"Telegram bot: @{bot.get('username', 'unknown')}")
        print(f"Telegram chat: {chat.get('title', chat_id)}")
    if "vk" in targets:
        if os.getenv("VK_ACCESS_TOKEN") and os.getenv("VK_GROUP_ID"):
            group_id = resolve_vk_group_id()
            group = vk_api(
                "groups.getById",
                {"group_id": str(group_id), "fields": "screen_name"},
            )[0]
            print(
                f"VK community: {group.get('name', group_id)} "
                f"(@{group.get('screen_name', group_id)}, id {group_id})"
            )
        else:
            project_id, account_id, account_name = discover_postmypost_vk()
            print(
                f"Postmypost VK account: {account_name} "
                f"(project {project_id}, account {account_id})"
            )
    if "instagram" in targets:
        instagram_token, instagram_user_id = require_env(
            "IG_ACCESS_TOKEN", "IG_USER_ID"
        )
        instagram_version = os.getenv("IG_API_VERSION", "v25.0")
        instagram = request_json(
            meta_url("graph.instagram.com", instagram_version, "me"),
            fields={"fields": "id,username", "access_token": instagram_token},
            method="GET",
        )
        if str(instagram.get("id")) != instagram_user_id:
            raise RuntimeError(
                "IG_USER_ID does not match the account returned by IG_ACCESS_TOKEN"
            )
        posts, _, _ = load_content()
        image_post = next((post for post in posts if post.get("image")), None)
        if image_post is None:
            raise RuntimeError("No image posts available for Instagram check")
        first_image = instagram_image_path(ROOT / image_post["image"])
        public_image_url = upload_public_image(first_image)
        with urllib.request.urlopen(public_image_url, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Instagram image URL returned HTTP {response.status}"
                )
        print(f"Instagram account: @{instagram.get('username', instagram_user_id)}")
        print(f"Instagram public image: {public_image_url}")
    if "facebook" in targets:
        facebook_token, facebook_page_id = require_env(
            "FB_PAGE_ACCESS_TOKEN", "FB_PAGE_ID"
        )
        facebook_version = os.getenv("FB_GRAPH_API_VERSION", "v25.0")
        facebook = request_json(
            meta_url("graph.facebook.com", facebook_version, facebook_page_id),
            fields={"fields": "id,name", "access_token": facebook_token},
            method="GET",
        )
        print(f"Facebook Page: {facebook.get('name', facebook_page_id)}")
    print(f"Enabled platforms: {', '.join(targets)}")
    print("Configuration check passed. Nothing was published.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--platform",
        choices=("all", "telegram", "vk", "instagram", "facebook"),
        default="all",
        help="Publish to every platform or resume only one of them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the next post without sending it.",
    )
    parser.add_argument(
        "--date",
        help="Use an ISO date instead of today's local date, useful for previews.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Publish immediately, ignoring calendar checks.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate all platform credentials without publishing.",
    )
    args = parser.parse_args()

    load_env()
    if args.check_config:
        check_config()
        return 0
    posts, dates, using_sheet_dates = load_content()
    calendar: dict[str, Any] = load_json(CALENDAR_PATH, {})
    state: dict[str, Any] = load_json(
        STATE_PATH, {"next_index": 0, "platforms": {}}
    )
    index = state["next_index"]
    if index >= len(posts):
        print("All prepared posts have already been published.")
        return 0
    if index >= len(dates):
        raise RuntimeError("Publishing calendar has fewer dates than prepared posts.")

    post = posts[index]
    image_value = post.get("image")
    image_path = ROOT / image_value if image_value else None
    if image_path is not None and not image_path.exists():
        raise RuntimeError(f"Image not found: {image_path}")

    completed = state["platforms"].setdefault(post["id"], {})
    all_targets = enabled_platforms()
    targets = all_targets if args.platform == "all" else (args.platform,)
    print(f"Post {index + 1}/{len(posts)}: {post['title']}")
    print(f"Image: {image_path if image_path is not None else 'none'}")
    now = local_now(calendar, args.date)
    today = now.date()
    scheduled_date = dates[index]
    scheduled_at = scheduled_datetime(scheduled_date, calendar)
    print(
        "Date: "
        f"{today.isoformat()}, scheduled: "
        f"{scheduled_at.strftime('%Y-%m-%d %H:%M')} "
        f"{calendar.get('timezone', 'Europe/Moscow')}"
    )
    if not args.force:
        if now < scheduled_at:
            print("Nothing due yet.")
            return 0
        if not using_sheet_dates and is_blocked(today, calendar):
            print("Today is blocked by the content calendar. Nothing sent.")
            return 0
    if args.dry_run:
        print(f"Already completed: {completed or 'none'}")
        print("Dry run: nothing sent.")
        return 0

    publishers = {
        "telegram": publish_telegram,
        "vk": publish_vk,
        "instagram": publish_instagram,
        "facebook": publish_facebook,
    }
    for target in targets:
        if completed.get(target):
            print(f"{target}: already sent, skipping")
            continue
        publishers[target](post, image_path)
        completed[target] = True
        save_state(state)
        print(f"{target}: sent")

    if all(completed.get(target) for target in all_targets):
        state["next_index"] += 1
        save_state(state)
        if state["next_index"] < len(posts):
            print(f"Advanced to post {state['next_index'] + 1}.")
        else:
            print("Published the final prepared post.")
    else:
        print("Post remains current until all enabled platforms succeed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
