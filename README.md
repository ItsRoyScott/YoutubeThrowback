# YouTube Throwback CLI

A command-line tool that scans a YouTube channel's upload history, caches the catalog locally, and finds "On This Day" anniversary videos published around a target date across past years.

---

## Features

* **Zero-Quota Channel Lookups:** Pass a channel name, handle (`@channel`), URL, or raw Channel ID. Channel names and handles are resolved via lightweight web scraping without consuming YouTube API units.
* **Smart Local Caching:** Scans a channel's full upload history once and saves it to `.cache/`. All subsequent date queries run locally in milliseconds.
* **Flexible Date Windows:** Look for videos uploaded on today's date or specify a date override (`-t 07-15`) with custom day tolerances (`-d 5`).
* **Clean JSON Exports:** Saves filtered anniversary results directly to `.exports/throwback_MM-DD.json`.
* **Persistent Authentication:** Saves authorized tokens locally in `_credentials/token.json` after the first login, so you do not have to re-authenticate in the browser on every run.

---

## Directory Structure

```text
YoutubeThrowback/
├── _credentials/             # OAuth secrets and session tokens (Do not commit)
│   ├── client_secret_*.json  # Downloaded Google OAuth credentials
│   └── token.json            # Generated automatically after first login
├── .cache/                   # Full channel upload catalogs stored locally
├── .exports/                 # Generated anniversary video JSON files
├── fetch_throwbacks.py       # Authentication and YouTube API helpers
├── get_channel_id.py         # 0-quota channel ID parser
├── scan_and_cache.py         # Main CLI application
└── test_auth.py              # Quick script to verify Google OAuth setup

```

---

## Installation & Setup

### 1. Clone the Repository & Install Dependencies

Ensure Python 3.9 or higher is installed on your system.

```bash
pip install google-auth-oauthlib google-api-python-client

```

### 2. Set Up Google OAuth 2.0 Credentials

To use the YouTube API, you need your own client credential file from the Google Cloud Console.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/?utm_source=gemini).
2. Create a new project (for example, `YouTube Throwback`).
3. Navigate to **APIs & Services > Library**, search for **YouTube Data API v3**, and click **Enable**.
4. Configure the **OAuth Consent Screen**:
* Go to **APIs & Services > OAuth consent screen** (or **Google Auth Platform**).
* Select **External** and click **Create**.
* Enter an Application Name (for example, `YoutubeThrowbackApp`) and user support email.
* Save and navigate to the **Audience** / **Test users** tab.
* Click **+ ADD USERS** and add your own Google email address.


5. Create **OAuth 2.0 Credentials**:
* Go to **APIs & Services > Credentials**.
* Click **+ CREATE CREDENTIALS** at the top and select **OAuth client ID**.
* Set **Application type** to **Web application**.
* Under **Authorized redirect URIs**, click **ADD URI** and add:
* `http://localhost:8000/`
* `[http://127.0.0.1:8000/](http://127.0.0.1:8000/)`


* Click **Create**.


6. Download the JSON credential file:
* Click **DOWNLOAD JSON** in the popup modal or under the **OAuth 2.0 Client IDs** table.
* Create a folder named `_credentials` inside the project directory.
* Save the downloaded JSON file directly into `_credentials/` (you do not need to rename it).



---

## Testing Authentication

Before running full scans, verify that your credentials and browser authorization flow are configured correctly.

Run the test script:

```bash
python test_auth.py

```

1. Your default web browser will open automatically.
2. Sign in with the Google account you added as a Test User.
3. On the *Google hasn't verified this app* warning, click **Continue**.
4. Grant read permissions for YouTube.
5. Once complete, return to your terminal. You should see your connected YouTube channel name and ID printed out.

A `token.json` file will now be saved in `_credentials/` to keep you logged in for future runs.

---

## Usage Examples

### Show Help Menu

```bash
python scan_and_cache.py ?

```

### Scan by Channel Name, Handle, or URL (Current Date)

You can pass a channel name in quotes, a handle, or a full URL:

```bash
python scan_and_cache.py "Democracy At Work"
python scan_and_cache.py @democracyatwork
python scan_and_cache.py https://www.youtube.com/@democracyatwork

```

### Specify Date Override & Day Tolerance

Look for videos uploaded around July 15th within a +/- 5 day window:

```bash
python scan_and_cache.py "Democracy At Work" -t 07-15 -d 5

```

### Force API Refresh

By default, the script loads channel data from `.cache/` if it exists. To ignore local cache and re-scan the channel via the YouTube API:

```bash
python scan_and_cache.py "Democracy At Work" --refresh

```

---

## Output Files

* **Cached Channel History:** Stored in `.cache/channel_<CHANNEL_ID>.json`
* **Anniversary Export:** Stored in `.exports/throwback_MM-DD.json`