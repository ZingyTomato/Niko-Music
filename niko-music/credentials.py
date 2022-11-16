import os, dotenv

dotenv.load_dotenv() ## Load enviroment variables.

### Bot Info
BOT_TOKEN = os.getenv("TOKEN")
VOTE_URL = os.getenv("VOTE_URL")
INVITE_URL = os.getenv("INVITE_URL")
SUPPORT_SERVER_URL = os.getenv("SUPPORT_SERVER_URL")

### Lavalink Server Info
LAVALINK_HOST = os.getenv("LAVAHOST")
LAVALINK_PORT = os.getenv("LAVAPORT")
LAVALINK_PASS = os.getenv("LAVAPASS")

### Spotify Credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTCLIENT")
SPOTIFY_TRENDING_ID = os.getenv("SPOTIFY_TRENDING_ID") ## The playlist ID used to retrieve trending tracks.

### Genius Credentials
GENIUS_API_KEY = os.getenv("GENIUSKEY")

### Logging
LOGGING_CHANNEL_ID = os.getenv("LOGID")