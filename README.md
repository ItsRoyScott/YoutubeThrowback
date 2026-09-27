```markdown
# YouTube Throwback CLI

A local command-line tool that scans YouTube channel upload histories, caches video metadata locally, and finds "On This Day" anniversary videos published on exact target dates across past years.

---

## Features

* **Zero-Quota Channel Lookups:** Pass channel names, handles (`@channel`), URLs, or raw Channel IDs. Channel resolution uses local scraping with zero API quota cost.
* **Batch Processing:** Pass a single channel or a `.txt` file containing multiple channels to process an entire list in sequence.
* **Dual Extraction Engines:**
  * **YouTube Data API v3 (Default):** Fast and precise for standard channels.
  * **Parallel `yt-dlp` (`-y` / `--ytdlp`):** Multi-threaded date-window scraping that bypasses YouTube's 20,000 video API cap for massive high-volume news channels.
* **Exact Matching & Custom Tolerances:** Defaults to exact date matching (0-day tolerance). Custom day ranges like `-d 3` (+/- 3 days) can be set when needed.
* **Offline Caching:** Saves full channel catalogs to `.cache/` to run instant date queries without repeating network requests.
* **Clean JSON Exports:** Outputs filtered anniversary results directly to `.exports/`.
* **Real-time Console Progress:** Displays live status indicators for API page fetches and parallel `yt-dlp` year scans.

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
├── get_channel_id.py         # 0-quota channel ID resolver
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

Follow the instructions in `_credentials/INSTRUCTIONS.md` to download your Google OAuth JSON file into the `_credentials/` directory, then verify your setup:

```bash
python test_auth.py

```

---

## Usage Examples

### View Help

```bash
python scan_and_cache.py ?

```

### Scan a Single Channel (Exact Date Match)

```bash
python scan_and_cache.py "Democracy At Work"
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

### Specify Date Override & Day Tolerance

Search for videos published around July 15th within a +/- 3 day window:

```bash
python scan_and_cache.py "Democracy At Work" -t 07-15 -d 3

```

### Scan High-Volume Channels (`yt-dlp` Parallel Engine)

Bypass the 20,000 video API limit for high-volume news outlets by enabling parallel `yt-dlp` scanning across past years:

```bash
python scan_and_cache.py "ABC News" -y

```

### Force Refresh Local Cache

To ignore existing `.cache/` files and force a re-scan:

```bash
python scan_and_cache.py "Democracy At Work" -f

```

---

## Output Files

* **Cached Channel Data:** Stored in `.cache/channel_<CHANNEL_ID>.json`
* **Exported Results:** Stored in `.exports/throwback_<CHANNEL_TITLE>_MM-DD.json`

```

```