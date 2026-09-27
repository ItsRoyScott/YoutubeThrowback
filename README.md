# YouTube Throwback CLI

A local command-line tool that automatically scans YouTube channel upload histories, caches video metadata locally, and extracts "On This Day" anniversary videos published on target dates across past years.

---

## Features

* **Smart Auto-Caching:** Automatically indexes full channel histories to `.cache/` on first run using low-cost API endpoints (1 quota unit per 50 videos). Subsequent queries on cached channels run instantly with zero API quota cost.
* **Zero-Quota Channel Lookups:** Pass channel names, handles (`@channel`), URLs, or raw Channel IDs. Resolves channel IDs locally without consuming API points.
* **Batch Processing:** Pass a single channel or a `.txt` file containing multiple channels to process an entire list sequentially.
* **Exact Matching and Custom Tolerances:** Defaults to exact date matching (0-day tolerance). Custom day ranges like `-d 3` (+/- 3 days) can be configured easily.
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

### View Help

```bash
python scan_and_cache.py ?

```

### Scan a Channel (Default Smart Auto-Cache)

On first run, the script automatically indexes the channel history to `.cache/`. Every future run on this channel uses local cache files for zero API cost.

```bash
python scan_and_cache.py "The Majority Report"
python scan_and_cache.py @democracyatwork
python scan_and_cache.py [https://www.youtube.com/@democracyatwork](https://www.youtube.com/@democracyatwork)

```

### Batch Process Multiple Channels

Create a text file (such as `channels.txt`) with one channel per line:

```text
# My Channel List
Democracy At Work
@democracyatwork
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

## Output Files

* **Cached Channel Data:** Stored in `.cache/channel_<CHANNEL_ID>.json`
* **Exported Results:** Stored in `.exports/throwback_<CHANNEL_TITLE>_MM-DD.json`
