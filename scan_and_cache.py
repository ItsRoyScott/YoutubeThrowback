import argparse
import concurrent.futures
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


def fetch_year_window(channel_id: str, year: int, target_month: int, target_day: int, day_tolerance: int) -> list:
    """Worker function to fetch videos for a single year using yt-dlp date filtering."""
    try:
        target_dt = datetime(year, target_month, target_day)
    except ValueError:
        target_dt = datetime(year, target_month, target_day - 1)

    start_dt = target_dt - timedelta(days=day_tolerance)
    end_dt = target_dt + timedelta(days=day_tolerance)

    date_after = start_dt.strftime("%Y%m%d")
    date_before = end_dt.strftime("%Y%m%d")

    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "daterange": yt_dlp.utils.DateRange(start=date_after, end=date_before)
    }

    matches = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if info and "entries" in info:
                for entry in info["entries"]:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    if not video_id:
                        continue
                    
                    upload_date = entry.get("upload_date")
                    if upload_date and len(upload_date) == 8:
                        published_at = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}T00:00:00Z"
                    else:
                        published_at = f"{year}-{target_month:02d}-{target_day:02d}T00:00:00Z"

                    matches.append({
                        "title": entry.get("title", "Untitled"),
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "published_at": published_at,
                        "year": year
                    })
        except Exception:
            pass

    return matches


def fetch_throwbacks_parallel_ytdlp(channel_id: str, target_month: int, target_day: int, day_tolerance: int = 0, start_year: int = 2006) -> list:
    """Scans prior years concurrently using a ThreadPoolExecutor with live progress updates."""
    current_year = datetime.now().year
    years = list(range(start_year, current_year + 1))
    all_matches = []
    total_years = len(years)
    completed_count = 0

    print(f"Scanning {total_years} prior years in parallel with yt-dlp threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_year_window, channel_id, yr, target_month, target_day, day_tolerance): yr
            for yr in years
        }

        for future in concurrent.futures.as_completed(futures):
            yr = futures[future]
            results = future.result()
            completed_count += 1
            all_matches.extend(results)
            print(f"  [Progress] Scanned year {yr} ({len(results)} video(s) found) [{completed_count}/{total_years} years complete]")

    all_matches.sort(key=lambda x: x["year"], reverse=True)
    return all_matches


def cache_channel_uploads(youtube, channel_id: str, force_refresh: bool = False) -> dict:
    """Fetches full upload history via YouTube API with live progress output."""
    cache_path = get_channel_cache_path(channel_id)

    if cache_path.exists() and not force_refresh:
        print(f"Loading channel history from cache: {cache_path.relative_to(BASE_DIR)}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"Scanning upload history for channel {channel_id} via YouTube API...")
    channel_title, uploads_id = get_channel_info(youtube, channel_id)

    videos = []
    next_page_token = None
    page = 0

    while True:
        page += 1
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

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
            "YouTube Throwback CLI: Scan channel uploads, cache data locally, and export anniversary videos.\n\n"
            "Channel Input Options:\n"
            "  1. Pass a single channel name, handle (@channel), URL, or raw Channel ID.\n"
            "  2. Pass a path to a .txt file containing one channel entry per line (e.g. channels.txt).\n\n"
            "Performance:\n"
            "  Use -y / --ytdlp for parallel date-window lookups on massive high-volume channels."
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
        "-f", "--refresh",
        action="store_true",
        help="Force re-scanning the channel, ignoring existing .cache files."
    )

    parser.add_argument(
        "-y", "--ytdlp",
        action="store_true",
        help="Use multi-threaded yt-dlp to bypass YouTube's 20,000 video API pagination cap."
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

    youtube = None
    if not args.ytdlp:
        youtube = get_youtube_client(scopes=SCOPES_READONLY)

    for index, channel_raw in enumerate(channels_to_process, start=1):
        print(f"=== Channel [{index}/{total_channels}]: '{channel_raw}' ===")
        
        try:
            channel_id = resolve_channel_id(channel_raw)

            if args.ytdlp:
                if not HAS_YTDLP:
                    raise RuntimeError("yt-dlp is not installed. Run 'pip install yt-dlp' to use this feature.")
                
                cache_path = get_channel_cache_path(channel_id)
                
                if cache_path.exists() and not args.refresh:
                    print(f"Loading channel history from cache: {cache_path.relative_to(BASE_DIR)}")
                    with open(cache_path, "r", encoding="utf-8") as f:
                        channel_cache = json.load(f)
                    throwbacks = query_throwbacks_from_cache(channel_cache, month, day, args.days)
                else:
                    throwbacks = fetch_throwbacks_parallel_ytdlp(
                        channel_id=channel_id,
                        target_month=month,
                        target_day=day,
                        day_tolerance=args.days
                    )
                    
                    channel_cache_data = {
                        "channel_id": channel_id,
                        "channel_title": f"Channel_{channel_id}",
                        "cached_at": datetime.now().isoformat(),
                        "total_videos": len(throwbacks),
                        "videos": throwbacks
                    }
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(channel_cache_data, f, indent=2, ensure_ascii=False)
                    
                    channel_cache = channel_cache_data
            else:
                channel_cache = cache_channel_uploads(
                    youtube=youtube,
                    channel_id=channel_id,
                    force_refresh=args.refresh
                )
                throwbacks = query_throwbacks_from_cache(channel_cache, month, day, args.days)

            if throwbacks:
                export_title = channel_cache.get("channel_title", channel_id)
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