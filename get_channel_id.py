import re
import urllib.parse
import urllib.request

def get_channel_id(query: str) -> str:
    """
    Finds a YouTube Channel ID from a channel name, handle, or URL without using API quota.
    
    Accepts:
      - Channel Name: "Democracy At Work"
      - Channel Handle: "@democracyatwork"
      - Full Channel URL: "https://www.youtube.com/@democracyatwork"
    """
    query = query.strip()

    # Determine target URL
    if query.startswith("@"):
        url = f"https://www.youtube.com/{query}"
    elif "youtube.com" in query or "youtu.be" in query:
        url = query
    else:
        # Search YouTube specifically filtered for Channels (sp=EgIQAg%253D%253D forces channel filter)
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAg%253D%253D"

    # YouTube blocks the default Python user-agent, so send a standard browser header
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Network error while reaching YouTube: {e}")

    # Regex search for 24-character YouTube channel IDs starting with 'UC'
    patterns = [
        r'"channelId":"(UC[\w-]{22})"',
        r'"browseId":"(UC[\w-]{22})"',
        r'/channel/(UC[\w-]{22})'
    ]

    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    raise ValueError(f"Could not find a Channel ID for query: '{query}'")


if __name__ == "__main__":
    test_queries = [
        "Democracy At Work",
        "@democracyatwork",
        "https://www.youtube.com/@democracyatwork"
    ]

    print("Testing Channel ID lookup (0 API Quota Used):\n")
    for q in test_queries:
        try:
            cid = get_channel_id(q)
            print(f"Query: '{q}'\n  -> Channel ID: {cid}\n")
        except Exception as err:
            print(f"Query: '{q}'\n  -> Error: {err}\n")