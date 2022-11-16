from responses.resp import Responses
from functions.func import Functions
import discord, wavelink, spotipy, lyricsgenius
from spotipy import SpotifyClientCredentials
from credentials import *
from time import strftime, gmtime
import random, re

class Music(Responses, Functions): 
    def __init__(self):
        self.discord = discord
        self.wavelink = wavelink
        
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,client_secret=SPOTIFY_CLIENT_SECRET))
        self.spot_exception = spotipy.client.SpotifyException ## Used to identify incorrect spotify results.
        
        self.genius = lyricsgenius.Genius(GENIUS_API_KEY) ## Used to retrieve lyrics.
        self.genius.verbose = False
        self.genius.remove_section_headers = True ## Removes [Chorus], [Intro] from the lyrics.
        self.genius.skip_non_songs = True

        self.err_color = 0xff0000 ## Used for unsucesful embeds.
        self.sucess_color = 0x33ee88 ## Used for sucessful embeds.
        self.trending_uri = SPOTIFY_TRENDING_ID ## The playlist ID used to retrieve trending tracks.
        self.vote_url = VOTE_URL
        self.invite_url = INVITE_URL
        self.support_url = SUPPORT_SERVER_URL
        self.strftime = strftime
        self.gmtime = gmtime
        self.random = random
        self.url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    
    def __await__(self):
        return self.async_init().__await__()