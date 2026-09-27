import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from fetch_throwbacks import (
    get_youtube_client,
    get_channel_info,
    SCOPES_READONLY
)
from get_channel_id import get_channel_id

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".cache"
EXPORTS_DIR = BASE_DIR / ".exports"

CACHE_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)


def parse_date(date_str: str) -> tuple[int, int]:
    """Parses date string formats like MM-DD, MM/DD, or YYYY-MM-DD into (month, day)."""
    clean_str = date_str.strip()
    
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.month, dt.day
        except ValueError:
            pass

    raise argparse.ArgumentTypeError(
        f"Invalid date format: '{date_str}'. Use MM-DD, MM/DD, or YYYY-MM-DD (e.g. 09-27 or 09/27)."
    )


def resolve_channel_id(channel_input: str) -> str:
    """Resolves raw IDs, channel names, handles, or URLs to a 24-character YouTube Channel ID."""
    clean_input = channel_input.strip()
    
    # If it is already a 24-character YouTube Channel ID starting with UC, return it directly
    if clean_input.startswith("UC") and len(clean_input) == 24:
        return clean_input

    print(f"Resolving '{clean_input}' to Channel ID without using API quota...")
    channel_id = get_channel_id(clean_input)
    print(f"Resolved Channel ID: {channel_id}\n")
    return channel_id


def get_channel_cache_path(channel_id: str) -> Path:
    return CACHE_DIR / f"channel_{channel_id}.json"


def cache_channel_uploads(youtube, channel_id: str, force_refresh: bool = False) -> dict:
    """Fetches full upload history from YouTube API or loads existing local JSON cache."""
    cache_path = get_channel_cache_path(channel_id)

    if cache_path.exists() and not force_refresh:
        print(f"Loading channel history from cache: {cache_path.relative_to(BASE_DIR)}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"Scanning upload history for channel {channel_id} via YouTube API...")
    channel_title, uploads_id = get_channel_info(youtube, channel_id)

    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "title": snippet["title"],
                "video_id": snippet["resourceId"]["videoId"],
                "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
                "published_at": snippet["publishedAt"]
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    cache_data = {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "cached_at": datetime.now().isoformat(),
        "total_videos": len(videos),
        "videos": videos
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully cached {len(videos)} videos to {cache_path.relative_to(BASE_DIR)}")
    return cache_data


def query_throwbacks_from_cache(cache_data: dict, target_month: int, target_day: int, day_tolerance: int = 3) -> list:
    """Filters local cache for videos uploaded around target month/day across all prior years."""
    matches = []

    for video in cache_data["videos"]:
        published_dt = datetime.strptime(video["published_at"], "%Y-%m-%dT%H:%M:%SZ")

        try:
            target_date_same_year = datetime(published_dt.year, target_month, target_day)
        except ValueError:
            target_date_same_year = datetime(published_dt.year, target_month, target_day - 1)

        diff_days = abs((published_dt - target_date_same_year).days)

        if diff_days <= day_tolerance:
            matches.append({
                "title": video["title"],
                "video_id": video["video_id"],
                "url": video["url"],
                "published_at": video["published_at"],
                "year": published_dt.year
            })

    return matches


def export_throwbacks_to_json(channel_title: str, target_month: int, target_day: int, day_tolerance: int, matches: list) -> Path:
    """Saves the filtered anniversary list to .exports/throwback_MM-DD.json."""
    filename = f"throwback_{target_month:02d}-{target_day:02d}.json"
    filepath = EXPORTS_DIR / filename

    output_data = {
        "channel_title": channel_title,
        "target_date": f"{target_month:02d}-{target_day:02d}",
        "day_tolerance": day_tolerance,
        "exported_at": datetime.now().isoformat(),
        "total_matches": len(matches),
        "videos": matches
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(matches)} throwback videos to {filepath.relative_to(BASE_DIR)}")
    return filepath


def main():
    # Map '?' argument to '--help' so CLI help triggers naturally
    if "?" in sys.argv:
        sys.argv[sys.argv.index("?")] = "--help"

    parser = argparse.ArgumentParser(
        description=(
            "YouTube Throwback CLI: Scan channel uploads, cache data locally, and export anniversary videos.\n\n"
            "Channel Resolution (0 API Quota Used):\n"
            "  You can pass a raw Channel ID, Channel Name, Handle, or URL directly.\n"
            "  Names, handles, and URLs are resolved via local HTML parsing with zero API unit cost."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )

    parser.add_argument(
        "channel",
        type=str,
        help=(
            "Target YouTube channel. Accepts four formats:\n"
            "  1. Channel Name  : \"Democracy At Work\"\n"
            "  2. Channel Handle: @democracyatwork\n"
            "  3. Channel URL   : https://www.youtube.com/@democracyatwork\n"
            "  4. Channel ID    : UCxHMVuopzdiAtwr5HkgrjKw"
        )
    )

    parser.add_argument(
        "-d", "--days",
        type=int,
        default=3,
        help="Day range tolerance (+/- number of days around target date). Default is 3."
    )

    parser.add_argument(
        "-t", "--date",
        type=str,
        default=None,
        help="Target date override formatted as MM-DD, MM/DD, or YYYY-MM-DD (e.g. 07-15). Default is today."
    )

    parser.add_argument(
        "-f", "--refresh",
        action="store_true",
        help="Force re-scanning the channel via YouTube API, ignoring existing .cache files."
    )

    args = parser.parse_args()

    if args.date:
        month, day = parse_date(args.date)
    else:
        today = datetime.now()
        month, day = today.month, today.day

    # Resolve input to channel ID
    channel_id = resolve_channel_id(args.channel)

    youtube = get_youtube_client(scopes=SCOPES_READONLY)

    channel_cache = cache_channel_uploads(youtube, channel_id, force_refresh=args.refresh)
    throwbacks = query_throwbacks_from_cache(channel_cache, month, day, args.days)

    if throwbacks:
        export_throwbacks_to_json(channel_cache["channel_title"], month, day, args.days, throwbacks)
        print("\nMatching videos found:")
        for v in throwbacks:
            print(f"  - [{v['year']}] {v['title']} ({v['url']})")
    else:
        print(f"\nNo matching videos found around {month:02d}-{day:02d} (+/- {args.days} days).")


if __name__ == "__main__":
    main()