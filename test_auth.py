from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope required to read YouTube account details
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

def find_client_secrets_file() -> Path:
    """Locates the client secrets JSON file inside the _credentials directory."""
    credentials_dir = Path(__file__).resolve().parent / "_credentials"
    matches = list(credentials_dir.glob("client_secret*.json"))
    
    if not matches:
        matches = list(credentials_dir.glob("*.json"))
        
    if not matches:
        raise FileNotFoundError(
            f"No JSON credential file found in {credentials_dir}. "
            "Please ensure your downloaded Google OAuth file is in that folder."
        )
    
    return matches[0]

def test_youtube_auth():
    secrets_path = find_client_secrets_file()
    print(f"Found credentials file: {secrets_path.name}")

    # Launch local authorization flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(secrets_path), 
        scopes=SCOPES
    )
    
    # Opens your default browser for Google sign-in
    credentials = flow.run_local_server(port=8000)

    # Initialize the YouTube Data API client
    youtube = build("youtube", "v3", credentials=credentials)

    # Query the authenticated user's channel details
    request = youtube.channels().list(
        part="snippet,statistics",
        mine=True
    )
    response = request.execute()

    if "items" in response and len(response["items"]) > 0:
        channel = response["items"][0]
        title = channel["snippet"]["title"]
        channel_id = channel["id"]
        subscribers = channel["statistics"].get("subscriberCount", "N/A")

        print("\nAuthentication successful.")
        print(f"Connected Channel: {title}")
        print(f"Channel ID: {channel_id}")
        print(f"Subscribers: {subscribers}")
    else:
        print("\nAuthenticated, but no YouTube channel is associated with this Google account.")

if __name__ == "__main__":
    test_youtube_auth()