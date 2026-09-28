# YouTube Throwback CLI

A local command-line tool that automatically scans YouTube channel upload histories, caches video metadata locally, extracts "On This Day" anniversary videos published on target dates across past years, and generates YouTube playlists directly on your account.

---

## Features

* **Smart Auto-Caching:** Automatically indexes full channel histories to `.cache/` on first run using low-cost API endpoints (1 quota unit per 50 videos). Features automatic cache expiration (refreshes if older than 180 days) and manual force flags (`-f`).
* **Zero-Quota Channel Lookups:** Pass channel names, handles (`@channel`), URLs, or raw Channel IDs. Resolves channel IDs locally without consuming API points.
* **Batch Processing & Aggregation:** Process single channels or `.txt` lists sequentially. Automatically generates single-channel exports and combined `.aggregate.json` files.
* **Exact Matching and Custom Tolerances:** Defaults to exact date matching (0-day tolerance) with optional custom ranges like `-d 3` (+/- 3 days).
* **Automated Playlist Generation:** Generates YouTube playlists directly on your account using `generate_playlist.py`. Includes options for 1-video-per-channel filtering (`-1`), overwrite checks (`-o`), exponential backoff retry logic, and dry runs (`-n`).
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
├── generate_playlist.py      # Automated YouTube playlist creation script
├── get_channel_id.py         # Zero-quota channel ID resolver
├── scan_and_cache.py         # Main CLI application
└── test_auth.py              # OAuth verification script
```

---

## Quick Setup

### 1. Install Dependencies

Ensure Python 3.9 or higher is installed, then run:

```bash
pip install google-auth-oauthlib google-api-python-client yt-dlp
```

### 2. Configure Google Credentials

Follow the instructions in `_credentials/INSTRUCTIONS.md` to place your Google OAuth JSON file into `_credentials/`, then verify setup:

```bash
python test_auth.py
```

---

## Usage Examples

### View CLI Help

```bash
python scan_and_cache.py ?
```

### Scan a Channel (Default Smart Auto-Cache)

Indexes full channel history on first run. Subsequent runs load from local cache with 0 API cost.

```bash
python scan_and_cache.py "The Majority Report"
python scan_and_cache.py @democracyatwrk
python scan_and_cache.py https://www.youtube.com/@democracyatwrk
```

### Batch Process Multiple Channels

Create a text file (such as `channels.txt`) with one channel per line:

```text
# My Channel List
Democracy At Work
@TheMajorityReport
ABC News
```

Run the script against the file:

```bash
python scan_and_cache.py channels.txt
```

### Specify Target Date and Day Tolerance

Search for anniversary videos published around July 15th within a +/- 3 day window:

```bash
python scan_and_cache.py "The Majority Report" -t 07-15 -d 3
```

### Force Refresh Local Cache (`-f`)

Re-sync local channel history from YouTube:

```bash
python scan_and_cache.py "The Majority Report" -f
```

### Live Targeted Search (`-l`)

Bypass local caching and perform a live year-by-year search via the API:

```bash
python scan_and_cache.py "The Majority Report" -l
```

---

## Generating Playlists

Use `generate_playlist.py` to create YouTube playlists from generated export files.

### 1. Generate Playlist from Newest Aggregate File

```bash
python generate_playlist.py
```

### 2. Limit to One Video Per Channel (`-1` / `--one-per-channel`)

```bash
python generate_playlist.py -1
```

### 3. Overwrite Existing Playlist (`-o` / `--overwrite`)

Replaces an existing playlist with the same title instead of creating a duplicate:

```bash
python generate_playlist.py -1 -o
```

### 4. Dry Run Mode (`-n` / `--dry-run`)

Preview playlist contents without making calls to YouTube:

```bash
python generate_playlist.py -1 --dry-run
```

---

## Output Files

* **Cached Channel Data:** Stored in `.cache/channel_<CHANNEL_ID>.json`
* **Single-Channel Exports:** Stored in `.exports/throwback_<CHANNEL_TITLE>_MM-DD.json`
* **Aggregate Batch Exports:** Stored in `.exports/throwback_MM-DD.aggregate.json`
