import argparse
import json
import sys
import time
import webbrowser
from pathlib import Path

try:
    from googleapiclient.errors import HttpError
except ImportError:
    HttpError = Exception

try:
    from fetch_throwbacks import get_youtube_client, SCOPES_READWRITE
except ImportError:
    from fetch_throwbacks import get_youtube_client
    SCOPES_READWRITE = ["https://www.googleapis.com/auth/youtube"]

BASE_DIR = Path(__file__).resolve().parent
EXPORTS_DIR = BASE_DIR / ".exports"


def find_latest_aggregate_file() -> Path:
    """Finds the most recently modified aggregate JSON file in .exports/."""
    if not EXPORTS_DIR.exists():
        raise FileNotFoundError("The .exports directory does not exist.")

    aggregate_files = sorted(
        EXPORTS_DIR.glob("*.aggregate.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not aggregate_files:
        all_exports = sorted(
            EXPORTS_DIR.glob("throwback_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not all_exports:
            raise FileNotFoundError(
                "No throwback export files found in .exports/ directory."
            )
        return all_exports[0]

    return aggregate_files[0]


def load_export_file(file_path: Path) -> dict:
    """Loads and validates JSON data from an export file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_one_per_channel(videos: list[dict]) -> list[dict]:
    """Filters video list to keep at most one video per channel."""
    seen_channels = set()
    filtered = []

    for video in videos:
        channel = video.get("channel_title", "Unknown")
        if channel not in seen_channels:
            seen_channels.add(channel)
            filtered.append(video)

    return filtered


def find_existing_playlist_id(youtube, title: str) -> str | None:
    """Searches user account for an existing playlist matching the exact title."""
    next_page_token = None
    while True:
        request = youtube.playlists().list(
            part="snippet", mine=True, maxResults=50, pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get("items", []):
            if item["snippet"]["title"] == title:
                return item["id"]

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return None


def create_youtube_playlist(
    youtube, title: str, description: str, privacy: str = "private"
) -> str:
    """Creates a new YouTube playlist and returns its playlist ID."""
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy},
        },
    )
    response = request.execute()
    return response["id"]


def add_videos_to_playlist(youtube, playlist_id: str, videos: list[dict]):
    """Adds a list of video objects to a YouTube playlist with retry logic for transient errors."""
    for idx, video in enumerate(videos, start=1):
        video_id = video["video_id"]
        title = video.get("title", "Untitled")
        channel = video.get("channel_title", "")

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id,
                            },
                        }
                    },
                )
                request.execute()
                print(f"  [{idx}/{len(videos)}] Added: {title} ({channel})")
                break
            except HttpError as err:
                status_code = getattr(getattr(err, "resp", None), "status", None)
                if status_code in (409, 500, 503) and attempt < max_retries:
                    wait_seconds = attempt * 2
                    print(
                        f"  [{idx}/{len(videos)}] Transient YouTube error ({status_code}) for '{title}'. Retrying in {wait_seconds}s (attempt {attempt}/{max_retries})..."
                    )
                    time.sleep(wait_seconds)
                else:
                    print(f"  [{idx}/{len(videos)}] Failed to add '{title}': {err}")
                    break
            except Exception as err:
                print(f"  [{idx}/{len(videos)}] Failed to add '{title}': {err}")
                break


def main():
    if "?" in sys.argv:
        sys.argv[sys.argv.index("?")] = "--help"

    parser = argparse.ArgumentParser(
        description=(
            "Generate YouTube Playlist from export files.\n\nDefaults to the"
            " most recently generated aggregate JSON file in .exports/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "export_file",
        nargs="?",
        default=None,
        help=(
            "Path or filename of the export JSON in .exports/ (defaults to the"
            " newest .aggregate.json)."
        ),
    )

    parser.add_argument(
        "-1",
        "--one-per-channel",
        action="store_true",
        help="Limit playlist items to at most one video per channel.",
    )

    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help=(
            "Overwrite an existing playlist if one with the same title already"
            " exists."
        ),
    )

    parser.add_argument(
        "-t",
        "--title",
        type=str,
        default=None,
        help="Custom title for the YouTube playlist.",
    )

    parser.add_argument(
        "-p",
        "--privacy",
        type=str,
        choices=["private", "unlisted", "public"],
        default="private",
        help="Playlist privacy status (default: private).",
    )

    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help=(
            "Preview the videos that would be added without creating the"
            " playlist."
        ),
    )

    args = parser.parse_args()

    if args.export_file:
        target_path = Path(args.export_file)
        if not target_path.exists():
            target_path = EXPORTS_DIR / args.export_file
        if not target_path.exists():
            raise FileNotFoundError(f"Export file not found: {args.export_file}")
    else:
        target_path = find_latest_aggregate_file()

    print(f"Loading export file: {target_path.relative_to(BASE_DIR)}")
    data = load_export_file(target_path)
    videos = data.get("videos", [])

    if not videos:
        print("No videos found in the selected export file.")
        return

    if args.one_per_channel:
        videos = filter_one_per_channel(videos)
        print(f"Filtered to {len(videos)} video(s) (1 per channel).")

    target_date = data.get("target_date", "Throwbacks")
    playlist_title = (
        args.title if args.title else f"YouTube Throwbacks ({target_date})"
    )

    if args.dry_run:
        print(f"\n[Dry Run] Would create playlist '{playlist_title}' with:")
        for v in videos:
            print(
                f"  - [{v.get('channel_title', 'Unknown')}] {v['title']} ({v['url']})"
            )
        return

    print(
        "\nAuthenticating with YouTube (Write permissions required for"
        " playlists)..."
    )
    youtube = get_youtube_client(scopes=SCOPES_READWRITE)

    existing_playlist_id = find_existing_playlist_id(youtube, playlist_title)

    if existing_playlist_id:
        if not args.overwrite:
            playlist_url = f"https://www.youtube.com/playlist?list={existing_playlist_id}"
            print(
                f"\n[Warning] Playlist '{playlist_title}' already exists"
                f" ({playlist_url})."
            )
            print(
                "Aborting playlist creation to conserve API quota. Pass"
                " '--overwrite' (or '-o') to replace it:"
            )
            print(
                f"  python generate_playlist.py"
                f" {'-1 ' if args.one_per_channel else ''}--overwrite"
            )
            return
        else:
            print(
                f"Found existing playlist '{playlist_title}' ({existing_playlist_id})."
                " Overwriting (--overwrite set)..."
            )
            youtube.playlists().delete(id=existing_playlist_id).execute()

    print(f"Creating {args.privacy} playlist: '{playlist_title}'...")
    playlist_id = create_youtube_playlist(
        youtube,
        playlist_title,
        "Auto-generated throwback playlist",
        privacy=args.privacy,
    )

    print(f"Adding {len(videos)} video(s) to playlist...")
    add_videos_to_playlist(youtube, playlist_id, videos)

    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"\nSuccessfully created playlist: {playlist_url}")

    print("Opening playlist in your web browser...")
    webbrowser.open(playlist_url)


if __name__ == "__main__":
    main()