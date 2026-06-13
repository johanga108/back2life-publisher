# Back2Life scheduled posts

This folder contains a 57-post publishing plan for Telegram, VK, and
Instagram: 28 visual posts about detention experience plus 29 short
practice/life posts whose images are still pending. Facebook Page support is
optional and currently disabled.

## Contents

- `assets/posts/`: 28 generated portrait images for the visual series.
- `assets/instagram/`: JPEG copies uploaded to Cloudinary one image post at a
  time for Instagram's public-URL publishing API.
- `assets/telegram/`: square JPEG copies for Telegram previews.
- `content/posts.json`: post order, titles, image paths, and captions.
- `content/publishing-calendar.json`: allowed publication dates, 19:00 Moscow
  publication time, and conflict rules.
- `content/connect-socials.md`: Russian setup checklist for all platforms.
- `scripts/publish_next.py`: sends the next post to enabled platforms.
- `state/publisher-state.json`: generated automatically after the first send.

## Configure channels

Follow the Russian checklist in `content/connect-socials.md`. Do not send
tokens through chat. Keep them only in the local `.env` file.

After configuration, validate every channel without sending a post:

```bash
python3 scripts/publish_next.py --check-config
```

Preview the first scheduled publication on June 8, 2026:

```bash
python3 scripts/publish_next.py --dry-run --date 2026-06-08
```

Send a post immediately during setup only:

```bash
python3 scripts/publish_next.py --force
```

The publisher saves progress after each successful platform send. If one API
fails, rerun the command: the successful platform will not receive a duplicate.
The automation should run once per day at 19:00 Europe/Moscow. On non-due,
early, or blocked dates the publisher exits without sending anything.

The editable source for publication dates, titles, and post texts is the
Google Sheets tab `Codex`. The publisher downloads it before each run. Image
paths remain fixed in `content/posts.json`; practice/life posts need generated
images before they can be published to Instagram.

## Calendar assumptions

- Visual series starts on Monday, June 8, 2026 and repeats every four days.
- Practice/life series starts on Wednesday, June 10, 2026 and repeats
  every four days.
- Together they create one post every two days.
- All posts publish at 19:00 Europe/Moscow.
- Sundays and month-end dates are allowed in this merged plan so the two
  four-day sequences stay interleaved exactly as requested.

## Visual direction

The selected images use a consistent editorial language: one human-scale
symbol, soft natural light, restrained Kodak Portra color, cinematic
documentary realism, and no motivational text on the image.
