import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from fetch_throwbacks import (
    get_youtube_client,
    get_channel_info,
    SCOPES_READONLY
)
from get_channel_id import get_channel_id

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".cache"
EXPORTS_DIR = BASE_DIR / ".exports"

CACHE_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class QuietLogger:
    """Custom logger to suppress yt-dlp stderr output during bot challenges."""
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


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
        f"Invalid date format: '{date_str}'. Use MM-DD, MM/DD, or YYYY-MM-DD (for example 09-27 or 09/27)."
    )


def resolve_channel_inputs(channel_input: str) -> list[str]:
    """Determines whether the input is a path to a text file or a single channel string."""
    potential_file = Path(channel_input)
    
    if potential_file.is_file():
        print(f"Reading channel list from file: {potential_file.name}")
        with open(potential_file, "r", encoding="utf-8") as f:
            channels = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        
        if not channels:
            raise ValueError(f"File '{potential_file}' contains no valid channel entries.")
        return channels

    return [channel_input.strip()]


def resolve_channel_id(channel_input: str) -> str:
    """Resolves raw IDs, channel names, handles, or URLs to a 24-character YouTube Channel ID."""
    clean_input = channel_input.strip()
    
    if clean_input.startswith("UC") and len(clean_input) == 24:
        return clean_input

    print(f"Resolving '{clean_input}' to Channel ID without using API quota...")
    channel_id = get_channel_id(clean_input)
    print(f"  -> Resolved Channel ID: {channel_id}")
    return channel_id


def get_channel_cache_path(channel_id: str) -> Path:
    return CACHE_DIR / f"channel_{channel_id}.json"


def cache_channel_uploads(youtube, channel_id: str, force_refresh: bool = False) -> dict:
    """Fetches full upload history via low-cost YouTube API playlist items."""
    cache_path = get_channel_cache_path(channel_id)

    if cache_path.exists() and not force_refresh:
        print(f"Loading channel history from local cache: {cache_path.relative_to(BASE_DIR)}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"Caching full upload history for channel {channel_id} via YouTube API...")
    channel_title, uploads_id = get_channel_info(youtube, channel_id)

    videos = []
    next_page_token = None
    page = 0

    while True:
        page += 1
        try:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
        except Exception as err:
            print(f"  [Notice] API scan stopped: {err}")
            break

        items = response.get("items", [])
        for item in items:
            snippet = item["snippet"]
            videos.append({
                "title": snippet["title"],
                "video_id": snippet["resourceId"]["videoId"],
                "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
                "published_at": snippet["publishedAt"]
            })

        print(f"  [API Progress] Fetched page {page} ({len(videos)} total videos logged)")

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


def query_throwbacks_from_cache(cache_data: dict, target_month: int, target_day: int, day_tolerance: int = 0) -> list:
    """Filters local cache for videos uploaded on target month/day across all prior years."""
    matches = []

    for video in cache_data["videos"]:
        if video.get("published_at") == "1970-01-01T00:00:00Z":
            continue

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


def fetch_single_year_api_search(youtube, channel_id: str, year: int, target_month: int, target_day: int, day_tolerance: int) -> tuple[list, bool]:
    """Queries YouTube API search endpoint for a specific year window."""
    try:
        target_dt = datetime(year, target_month, target_day)
    except ValueError:
        target_dt = datetime(year, target_month, target_day - 1)

    start_dt = target_dt - timedelta(days=day_tolerance)
    end_dt = target_dt + timedelta(days=day_tolerance, hours=23, minutes=59, seconds=59)

    published_after = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    published_before = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            publishedAfter=published_after,
            publishedBefore=published_before,
            maxResults=50
        )
        response = request.execute()

        matches = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            matches.append({
                "title": snippet["title"],
                "video_id": item["id"]["videoId"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "published_at": snippet["publishedAt"],
                "year": year
            })
        return matches, False
    except Exception as err:
        err_str = str(err)
        if "quotaExceeded" in err_str or "429" in err_str or "rateLimitExceeded" in err_str:
            return [], True
        print(f"  [Warning] Error fetching year {year}: {err}")
        return [], False


def fetch_throwbacks_via_targeted_search(youtube, channel_id: str, target_month: int, target_day: int, day_tolerance: int = 0, start_year: int = 2006) -> tuple[list, bool]:
    """Scans prior years using targeted API search queries."""
    current_year = datetime.now().year
    years = list(range(start_year, current_year + 1))
    all_matches = []
    quota_hit = False
    
    print(f"Executing live year-by-year search across {len(years)} prior years...")

    for yr in years:
        results, quota_exceeded = fetch_single_year_api_search(youtube, channel_id, yr, target_month, target_day, day_tolerance)
        
        if quota_exceeded:
            print("\n  [Notice] Google API daily Search Queries limit reached.")
            quota_hit = True
            break

        all_matches.extend(results)
        if results:
            print(f"  [Found] Year {yr}: {len(results)} video(s)")

    all_matches.sort(key=lambda x: x["year"], reverse=True)
    return all_matches, quota_hit


def fetch_ytdlp_fallback(channel_id: str, channel_name: str, target_month: int, target_day: int, day_tolerance: int = 0, browser: str = None) -> list:
    """Zero-quota fallback using yt-dlp with mobile client emulation."""
    if not HAS_YTDLP:
        return []

    month_name = MONTH_NAMES[target_month]
    search_query = f'ytsearch60:"{channel_name}" "{month_name} {target_day}"'
    print(f"Executing zero-quota search fallback via yt-dlp: {search_query}...")

    ydl_opts_flat = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "socket_timeout": 10,
        "logger": QuietLogger(),
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "android"]
            }
        }
    }
    if browser:
        ydl_opts_flat["cookiesfrombrowser"] = (browser,)

    candidate_ids = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries", []) if info else []
            for entry in entries:
                if entry and entry.get("id"):
                    candidate_ids.append(entry.get("id"))
    except Exception:
        pass

    if not candidate_ids:
        return []

    print(f"  [yt-dlp] Found {len(candidate_ids)} candidate videos. Verifying channel ownership and publication dates...")

    ydl_opts_detail = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "socket_timeout": 10,
        "logger": QuietLogger(),
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "android"]
            }
        }
    }

    matched_videos = []
    for vid in candidate_ids:
        try:
            with yt_dlp.YoutubeDL(ydl_opts_detail) as ydl:
                v_info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            if not v_info:
                continue

            v_channel_id = v_info.get("channel_id") or v_info.get("uploader_id")
            if v_channel_id and v_channel_id != channel_id:
                continue

            upload_date = v_info.get("upload_date")
            if not upload_date or len(upload_date) != 8:
                continue

            yr = int(upload_date[:4])
            m = int(upload_date[4:6])
            d = int(upload_date[6:8])

            try:
                target_dt = datetime(yr, target_month, target_day)
            except ValueError:
                target_dt = datetime(yr, target_month, target_day - 1)

            video_dt = datetime(yr, m, d)
            diff_days = abs((video_dt - target_dt).days)

            if diff_days <= day_tolerance:
                published_at = f"{yr}-{m:02d}-{d:02d}T00:00:00Z"
                matched_videos.append({
                    "title": v_info.get("title", "Untitled"),
                    "video_id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published_at": published_at,
                    "year": yr
                })
        except Exception:
            continue

    matched_videos.sort(key=lambda x: x["year"], reverse=True)
    return matched_videos


def export_throwbacks_to_json(channel_title: str, target_month: int, target_day: int, day_tolerance: int, matches: list) -> Path:
    """Saves the filtered anniversary list to .exports/throwback_MM-DD.json."""
    clean_title = "".join(c for c in channel_title if c.isalnum() or c in (" ", "_", "-")).strip()
    filename = f"throwback_{clean_title}_{target_month:02d}-{target_day:02d}.json"
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
    if "?" in sys.argv:
        sys.argv[sys.argv.index("?")] = "--help"

    parser = argparse.ArgumentParser(
        description=(
            "YouTube Throwback CLI: Automatically caches channel histories and extracts 'On This Day' anniversary videos.\n\n"
            "Channel Input Options:\n"
            "  1. Pass a single channel name, handle (@channel), URL, or raw Channel ID.\n"
            "  2. Pass a path to a .txt file containing one channel entry per line (for example channels.txt)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )

    parser.add_argument(
        "channel",
        type=str,
        help="Target YouTube channel name, handle, URL, Channel ID, or path to a .txt channel list file."
    )

    parser.add_argument(
        "-d", "--days",
        type=int,
        default=0,
        help="Day range tolerance (+/- number of days around target date). Default is 0 (exact date match)."
    )

    parser.add_argument(
        "-t", "--date",
        type=str,
        default=None,
        help="Target date override formatted as MM-DD, MM/DD, or YYYY-MM-DD. Default is today."
    )

    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force re-syncing full channel history to .cache/, ignoring existing local files."
    )

    parser.add_argument(
        "-l", "--live",
        action="store_true",
        help="Bypass full local caching and run a live year-by-year search via API."
    )

    parser.add_argument(
        "-cb", "--cookies-from-browser",
        type=str,
        default=None,
        help="Specify browser name (for example chrome, firefox, edge, brave) to pass authentication cookies to yt-dlp."
    )

    args = parser.parse_args()

    if args.date:
        month, day = parse_date(args.date)
    else:
        today = datetime.now()
        month, day = today.month, today.day

    channels_to_process = resolve_channel_inputs(args.channel)
    total_channels = len(channels_to_process)
    print(f"Found {total_channels} channel(s) to process.\n")

    youtube = get_youtube_client(scopes=SCOPES_READONLY)

    for index, channel_raw in enumerate(channels_to_process, start=1):
        print(f"=== Channel [{index}/{total_channels}]: '{channel_raw}' ===")
        
        try:
            channel_id = resolve_channel_id(channel_raw)
            cache_path = get_channel_cache_path(channel_id)

            if args.live:
                throwbacks, quota_hit = fetch_throwbacks_via_targeted_search(
                    youtube=youtube,
                    channel_id=channel_id,
                    target_month=month,
                    target_day=day,
                    day_tolerance=args.days
                )

                if quota_hit:
                    if cache_path.exists():
                        print(f"  [Fallback] Quota reached. Loading local cache: {cache_path.relative_to(BASE_DIR)}")
                        with open(cache_path, "r", encoding="utf-8") as f:
                            channel_cache = json.load(f)
                        throwbacks = query_throwbacks_from_cache(channel_cache, month, day, args.days)
                    elif HAS_YTDLP:
                        throwbacks = fetch_ytdlp_fallback(
                            channel_id=channel_id,
                            channel_name=channel_raw,
                            target_month=month,
                            target_day=day,
                            day_tolerance=args.days,
                            browser=args.cookies_from_browser
                        )

                channel_cache = {"channel_title": channel_raw}

            else:
                channel_cache = cache_channel_uploads(
                    youtube=youtube,
                    channel_id=channel_id,
                    force_refresh=args.force
                )
                throwbacks = query_throwbacks_from_cache(channel_cache, month, day, args.days)

            if throwbacks:
                export_title = channel_cache.get("channel_title", channel_raw)
                export_throwbacks_to_json(export_title, month, day, args.days, throwbacks)
                print(f"\nMatching videos found ({len(throwbacks)}):")
                for v in throwbacks[:10]:
                    print(f"  - [{v['year']}] {v['title']} ({v['url']})")
                if len(throwbacks) > 10:
                    print(f"  ... and {len(throwbacks) - 10} more (see export file)")
            else:
                print(f"\nNo matching videos found on {month:02d}-{day:02d} across past years.")

        except Exception as e:
            print(f"Error processing channel '{channel_raw}': {e}")

        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    main()