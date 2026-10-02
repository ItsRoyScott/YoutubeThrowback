from datetime import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES_READONLY = ["https://www.googleapis.com/auth/youtube.readonly"]
SCOPES_READWRITE = ["https://www.googleapis.com/auth/youtube"]
SCOPES_FULL = SCOPES_READWRITE


def find_client_secrets_file() -> Path:
    """Locates the client secrets JSON file inside the _credentials directory."""
    credentials_dir = Path(__file__).resolve().parent / "_credentials"
    matches = list(credentials_dir.glob("client_secret*.json")) or list(
        credentials_dir.glob("*.json")
    )
    if not matches:
        raise FileNotFoundError(
            f"No JSON credential file found in {credentials_dir}. "
            "Please ensure your Google OAuth JSON file is in that folder."
        )
    return matches[0]


def get_youtube_client(scopes=None):
    """
    Returns an authenticated YouTube API client service.
    Defaults to SCOPES_READWRITE so initial login grants playlist write permissions upfront.
    Automatically re-authenticates if cached token lacks requested scopes.
    """
    if scopes is None:
        scopes = SCOPES_READWRITE

    credentials_dir = Path(__file__).resolve().parent / "_credentials"
    token_path = credentials_dir / "token.json"
    credentials = None

    # 1. Load cached token if available and verify it satisfies requested scopes
    if token_path.exists():
        try:
            # Note: Do not pass `scopes` to `from_authorized_user_file` here. Passing `scopes`
            # causes google-auth to override `credentials.scopes` with the requested parameter,
            # which tricks `has_scopes()` into returning True even if token.json is read-only.
            credentials = Credentials.from_authorized_user_file(str(token_path))
            if not credentials.has_scopes(scopes):
                # Cached token lacks requested scopes; trigger fresh login to upgrade scope
                credentials = None
        except Exception:
            credentials = None

    # 2. Refresh token if expired, or launch browser login if missing/insufficient
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                credentials = None

        if not credentials or not credentials.valid:
            secrets_path = find_client_secrets_file()
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_path), scopes=scopes
            )
            credentials = flow.run_local_server(
                port=8000, prompt="consent", access_type="offline"
            )

        # 3. Save updated token to disk
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(credentials.to_json())

    return build("youtube", "v3", credentials=credentials)


def get_channel_info(youtube, channel_id: str):
    """Fetches channel title and uploads playlist ID."""
    response = (
        youtube.channels()
        .list(part="snippet,contentDetails", id=channel_id)
        .execute()
    )

    items = response.get("items", [])
    if not items:
        raise ValueError(f"Channel ID '{channel_id}' not found.")

    title = items[0]["snippet"]["title"]
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return title, uploads_id


def fetch_throwback_videos(
    youtube,
    uploads_playlist_id: str,
    target_month: int,
    target_day: int,
    day_tolerance: int = 3,
):
    """Fetches videos matching month/day target across past years."""
    matched_videos = []
    next_page_token = None

    print(
        f"Scanning uploads around {target_month:02d}-{target_day:02d} (+/-"
        f" {day_tolerance} days)..."
    )

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            published_str = snippet["publishedAt"]
            published_dt = datetime.strptime(
                published_str, "%Y-%m-%dT%H:%M:%SZ"
            )

            try:
                target_date_same_year = datetime(
                    published_dt.year, target_month, target_day
                )
            except ValueError:
                target_date_same_year = datetime(
                    published_dt.year, target_month, target_day - 1
                )

            diff_days = abs((published_dt - target_date_same_year).days)

            if diff_days <= day_tolerance:
                matched_videos.append({
                    "title": snippet["title"],
                    "video_id": snippet["resourceId"]["videoId"],
                    "url": (
                        "https://www.youtube.com/watch?v="
                        f"{snippet['resourceId']['videoId']}"
                    ),
                    "published_at": published_str,
                    "year": published_dt.year,
                })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return matched_videos