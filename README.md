# YouTube Throwback CLI

A local command-line tool that automatically scans YouTube channel upload histories, caches video metadata locally, and finds "On This Day" anniversary videos published on target dates across past years.

---

## Features

* **Smart Auto-Caching:** Automatically indexes full channel histories to `.cache/` on first run using low-cost API endpoints (1 quota unit per 50 videos). Subsequent queries on cached channels run instantly with 0 API quota cost.
* **Zero-Quota Channel Lookups:** Pass channel names, handles (`@channel`), URLs, or raw Channel IDs. Resolves channel IDs locally without consuming API points.
* **Batch Processing:** Pass a single channel or a `.txt` file containing multiple channels to process an entire list sequentially.
* **Exact Matching & Custom Tolerances:** Defaults to exact date matching (0-day tolerance). Custom day ranges like `-d 3` (+/- 3 days) can be configured easily.
* **Clean JSON Exports:** Outputs filtered anniversary results directly to `.exports/`.
* **Zero-Quota Fallback:** Includes a `yt-dlp` fallback engine to handle API quota exhaustion smoothly.

---

## Directory Structure

```text
YoutubeThrowback/
├── _credentials/             # OAuth secrets and setup instructions
│   ├── INSTRUCTIONS.md       # Google Cloud OAuth setup guide
│   ├── client_secret_*.json  # Google OAuth client secret
│   └── token.json            # Persistent user session token
├── .cache/                   # Cached raw channel upload histories
├── .exports/                 # Generated anniversary video JSON files
├── fetch_throwbacks.py       # Authentication and YouTube API helpers
├── get_channel_id.py         # Zero-quota channel ID resolver
├── scan_and_cache.py         # Main CLI application
└── test_auth.py              # OAuth verification script