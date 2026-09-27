# generate_playlist.py
import json
from datetime import datetime
from pathlib import Path
from fetch_throwbacks import (
    get_youtube_client,
    get_channel_info,
    fetch_throwback_videos,
    SCOPES_FULL
)

def export_to_json(channel_title: str, target_month: int, target_day: int, day_tolerance: int, videos: list) -> Path:
    output_dir = Path(__file__).resolve().parent / "exports"
    output_dir.mkdir(exist_ok=True)

    filename = f"throwback_{target_month:02d}-{target_day:02d}.json"
    filepath = output_dir / filename

    data = {
        "channel_title": channel_title,
        "target_date": f"{target_month:02d}-{target_day:02d}",
        "day_tolerance": day_tolerance,
        "exported_at": datetime.now().isoformat(),
        "total_matches": len(videos),
        "videos": videos
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON export to: {filepath}")
    return filepath

def create_youtube_playlist(youtube, title: str, description: str, video_ids: list):
    print("\nCreating new private YouTube playlist...")
    
    playlist = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    ).execute()

    playlist_id = playlist["id"]
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Playlist created: {playlist_url}")
    print(f"Adding {len(video_ids)} videos to playlist...")

    for index, vid_id in enumerate(video_ids, start=1):
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": vid_id
                    }
                }
            }
        ).execute()
        print(f"  [{index}/{len(video_ids)}] Added video {vid_id}")

    print(f"\nSuccessfully populated playlist: {playlist_url}")
    return playlist_url

if __name__ == "__main__":
    # Initialize client using full playlist creation scope imported from fetch_throwbacks
    youtube = get_youtube_client(scopes=SCOPES_FULL)

    target_channel_id = "UCxHMVuopzdiAtwr5HkgrjKw"
    today = datetime.now()
    month, day = today.month, today.day
    tolerance = 3

    # Reusing functions imported from fetch_throwbacks.py
    channel_name, uploads_id = get_channel_info(youtube, target_channel_id)
    matches = fetch_throwback_videos(youtube, uploads_id, month, day, tolerance)

    if not matches:
        print("No throwback videos found for this date range.")
    else:
        export_to_json(channel_name, month, day, tolerance, matches)

        user_choice = input("\nWould you like to create a YouTube playlist from these videos? (y/n): ").strip().lower()

        if user_choice == "y":
            playlist_title = f"{channel_name} - On This Day ({month:02d}/{day:02d})"
            playlist_desc = f"Throwback videos from {channel_name} around {month:02d}/{day:02d} across prior years."
            video_ids = [v["video_id"] for v in matches]

            create_youtube_playlist(youtube, playlist_title, playlist_desc, video_ids)
        else:
            print("Skipped playlist creation.")