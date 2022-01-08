import discord
import wavelink
from discord.ext import commands 
import typing as t
import asyncio
import re
import datetime as dt
import random
from enum import Enum
import aiohttp
import lyricsgenius
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
from discord_components import DiscordComponents, ComponentsBot, Button
from ytmusicapi import YTMusic
import os
import urllib.parse as urlparse

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
TIME_REGEX = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"

class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass
    
class QueueIsEmpty(commands.CommandError):
    pass

class NoTracksFound(commands.CommandError):
    pass
    
class PlayerIsAlreadyPaused(commands.CommandError):
    pass
    
class NoMoreTracks(commands.CommandError):
    pass

class NoPreviousTracks(commands.CommandError):
    pass
    
class VolumeTooLow(commands.CommandError):
    pass


class VolumeTooHigh(commands.CommandError):
    pass


class MaxVolume(commands.CommandError):
    pass


class MinVolume(commands.CommandError):
    pass
    
class NoLyricsFound(commands.CommandError):
    pass
    
class InvalidTimeString(commands.CommandError):
    pass
   
class InvalidEQPreset(commands.CommandError):
    pass

    
class RepeatMode(Enum):
    STOP = 0
    SONG = 1
    QUEUE = 2

class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.STOP

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        self._queue.extend(args)

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.QUEUE:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "stop":
            self.repeat_mode = RepeatMode.STOP
        elif mode == "song":
            self.repeat_mode = RepeatMode.SONG
        elif mode == "queue":
            self.repeat_mode = RepeatMode.QUEUE

    def empty(self):
        self._queue.clear()
        self.position = 0

class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        
    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self, ctx, tracks):

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)

        elif len(f"{tracks}".split('\n'))== 1:
            self.queue.add(tracks[0])
        else:
            if (track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)

        if not self.is_playing:
            await self.start_playback()
            
    async def choose_track(self, ctx, tracks):
            return tracks[0]

    async def start_playback(self):
        await self.play(self.queue.current_track)
        
    async def advance(self):
      try:
           if (track := self.queue.get_next_track()) is not None:
             await self.play(track)
           
      except QueueIsEmpty:
          pass
          
    async def repeat_track(self):
        await self.play(self.queue.current_track)

class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()
               
    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f"Music server is up!")
        
    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        if payload.player.queue.repeat_mode == RepeatMode.SONG:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()
    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply("Sorry, you can't use my music commands in a DM!", mention_author=False)
            return False

        return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "192.168.0.107",	
                "port": 2333,
                "rest_uri": "http://192.168.0.107:2333",
                "password": "nikomusic ",
                "identifier": "MAIN",
                "region": "asia",
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)


    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)
            
    @commands.command(name="connect", aliases=["join"])
    async def connect_command(self, ctx,  *,channel: t.Optional[discord.VoiceChannel]):
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        embed=discord.Embed(title=f"Joined voice channel.", color=discord.Colour.teal())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Joined VC in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
           
    @connect_command.error
    async def connect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            embed=discord.Embed(title=f"You are already in a voice chanel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
         
    @commands.command(name="disconnect", aliases=["leave"])
    async def disconnect_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await player.teardown()
        embed=discord.Embed(title=f"Left voice channel.", color=discord.Colour.red())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Left VC in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @disconnect_command.error
    async def disconnect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            embed=discord.Embed(title=f"You are already in a voice chanel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        
    @commands.command(name="play",pass_context=True)	
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)
        if not player.is_connected:
            await player.connect(ctx)
        query = query.strip("<>")
        if "youtube" in query:
          embed=discord.Embed(title="Supported Platforms : Soundcloud, Spotify, Bandcamp, Vimeo, Twitch and HTTP Streams.", color=discord.Colour.red())
          return await ctx.reply(embed=embed, mention_author=False)
        if "https://youtu.be/" in query:
          embed=discord.Embed(title="Supported Platforms : Soundcloud, Spotify, Bandcamp, Vimeo, Twitch and HTTP Streams.", color=discord.Colour.red())
          return await ctx.reply(embed=embed, mention_author=False)
        if "https://open.spotify.com/playlist" in query:
         sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
         playlist_link = f"{query}"
         playlist_URI = playlist_link.split("/")[-1].split("?")[0]
         track_uris = [x["track"]["uri"] for x in sp.playlist_tracks(playlist_URI)["items"]]
         for track in sp.playlist_tracks(playlist_URI)["items"]:
          track_name = track["track"]["name"]
          track_artist = track["track"]["artists"][0]["name"]
          queryfinal = f"{track_name} " + " " + f"{track_artist}" 
          result = f"ytmsearch:{queryfinal}"
          try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result))	
          except:
            pass
        if "https://open.spotify.com/album" in query:	
         sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
         album_link = f"{query}"
         album_id= album_link.split("/")[-1].split("?")[0]
         for track in sp.album_tracks(album_id)["items"]:
          track_name = track["name"]
          track_artist = track["artists"][0]["name"]
          queryfinal = f"{track_name} " + " " + f"{track_artist}" 
          result = f"ytmsearch:{queryfinal}"
          try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result))	
          except:
            pass
        if "https://deezer.com" in query:
          embed=discord.Embed(title="Supported Platforms : Soundcloud, Spotify, Bandcamp, Vimeo, Twitch and HTTP Streams.", color=discord.Colour.red())
          return await ctx.reply(embed=embed, mention_author=False)
        if "https://soundcloud.com" in query:
         print(query)
         await player.add_tracks(ctx, await self.wavelink.get_tracks(query))
        if "https://" in query:
         print(query)
         await player.add_tracks(ctx, await self.wavelink.get_tracks(query))   
        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty
        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
              async with ctx.typing():
                result = f"ytmsearch:{query}"
                await player.add_tracks(ctx, await self.wavelink.get_tracks(result))    
                sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
                results = sp.search(q=f'{query}', limit=1)
                for idx, track in enumerate(results['tracks']['items']):
                 querytrack = track['name']
                 print(querytrack)
                 queryartist = track["artists"][0]["name"]	
                embed=discord.Embed(title="Enqueued Track",color=discord.Colour.gold())
                try:
                  embed.add_field(name="Name", value=f"{querytrack}", inline=False)
                except:
                  embed.add_field(name="Name", value=f"{player.queue.current_track.title}", inline=False)
                try:
                  embed.add_field(name="Artist", value=f"{queryartist}", inline=False)
                except:
                  embed.add_field(name="Artist", value=f"{player.queue.current_track.author}", inline=False)
                try:
                  embed.add_field(name="Album", value=f"{track['album']['name']}", inline=False)
                except:
                  pass
                length = divmod(player.queue.current_track.length, 60000)
                embed.add_field(name="Duration", value=f"{int(length[0])}:{round(length[1]/1000):02}", inline=False)
                try:
                  embed.add_field(name="Release Date", value=f"{track['album']['release_date']}", inline=False)
                except:
                  pass
                try:
                  embed.set_thumbnail(url=f"{track['album']['images'][0]['url']}")
                except:
                  pass
                await ctx.reply(embed=embed, mention_author=False)
                channel = self.bot.get_channel(926147126180855850)
                embed=discord.Embed(description=f"``{ctx.author.name}`` is playing ``{player.queue.current_track.title}`` by ``{player.queue.current_track.author}`` in ``{ctx.message.guild.name}`` which is ``{int(length[0])}:{round(length[1]/1000):02}7`` seconds long!")
                await channel.send(embed=embed)
          
    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)	
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You are not in a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)          
          
    @commands.command(name="dl",pass_context=True)    
    async def play1_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)
        query = query.strip("<>")
        if not re.match(URL_REGEX, query):
          url = requests.get(f"http://192.168.0.109:5000/result/?query={query}")
          decode = json.loads(url.text)
          jiosong = decode[0]['media_url']
          song= decode[0]['song']
          os.system(f"youtube-dl -o '/home/zingy/music/%(title)s-%(id)s.%(ext)s' {jiosong} -x --audio-format mp3")
          name = os.listdir("/home/zingy/music")[0]
          os.rename(f"/home/zingy/music/{name}", f"/home/zingy/music/{song}.mp3")
          namefinal = os.listdir("/home/zingy/music")[0]
          await ctx.reply(file=discord.File(f"/home/zingy/music/{namefinal}"), mention_author=False)
          os.remove(f"/home/zingy/music/{namefinal}")
          
    @commands.command(name="jio",pass_context=True)    
    async def play2_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await ctx.guild.change_voice_state(channel=ctx.message.author.voice.channel, self_mute=False, self_deaf=True)
        query = query.strip("<>")
        if not re.match(URL_REGEX, query):
          url = requests.get(f"http://192.168.0.109:5000/result/?query={query}")
          decode = json.loads(url.text)
          jiosong = decode[0]['media_url']
          song= decode[0]['song']
          artist= decode[0]['singers']
          image= decode[0]['image']
          await player.add_tracks(ctx, await self.wavelink.get_tracks(jiosong))    
          embed=discord.Embed(description=f"Enqueued Track", color=discord.Colour.gold())
          embed.add_field(name="Title", value=f"{song}", inline=False)
          embed.add_field(name="Artist(s)", value=f"{artist}", inline=False)
          length = divmod(player.queue.current_track.length, 60000)
          embed.add_field(name=f"Duration", value=f"{int(length[0])}:{round(length[1]/1000):02}", inline=False)
          embed.set_thumbnail(url=f"{image}")
          await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="recommend",pass_context=True)    
    async def reccomend_command(self, ctx):
        player = self.get_player(ctx)
        if player.queue.is_empty:
           raise QueueIsEmpty
        try:
          url_data = urlparse.urlparse(f"{player.queue.current_track.uri}")
          query = urlparse.parse_qs(url_data.query)
          video = query["v"][0]
          print(video)
          embed=discord.Embed(title="Recommendations", description="Starting to add recommended tracks to the queue.", color=discord.Color.random())
          await ctx.reply(embed=embed, mention_author=False)
        except: 
          pass
        ytmusic = YTMusic()
        playlist = ytmusic.get_watch_playlist(videoId=f"{video}", limit=10)
        song1 = playlist["tracks"][1]["title"]
        print(song1)
        result = f"ytmsearch:{song1}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result))    
        except:
           pass
        song2 = playlist["tracks"][2]["title"]
        print(song2)
        result2 = f"ytmsearch:{song2}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result2))    
        except:
           pass
        song3 = playlist["tracks"][3]["title"]
        print(song3)
        result3 = f"ytmsearch:{song3}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result3))    
        except:
           pass
        song4 = playlist["tracks"][4]["title"]
        print(song4)
        result2 = f"ytmsearch:{song4}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result4))    
        except:
           pass
        song5 = playlist["tracks"][5]["title"]
        print(song5)
        result5 = f"ytmsearch:{song5}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result5))    
        except:
           pass
        song6 = playlist["tracks"][6]["title"]
        print(song6)
        result2 = f"ytmsearch:{song6}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result6))    
        except:
           pass
        song7 = playlist["tracks"][7]["title"]
        print(song7)
        result7 = f"ytmsearch:{song7}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result7))    
        except:
           pass
        song8 = playlist["tracks"][8]["title"]
        print(song8)
        result8 = f"ytmsearch:{song8}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result8))    
        except:
           pass
        song9 = playlist["tracks"][9]["title"]
        print(song9)
        result9 = f"ytmsearch:{song9}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result9))    
        except:
           pass
        song10 = playlist["tracks"][10]["title"]
        print(song10)
        result10 = f"ytmsearch:{song10}"
        try: 
            await player.add_tracks(ctx, await self.wavelink.get_tracks(result10))    
        except:
           pass
            
    @reccomend_command.error
    async def reccomend_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="pause")
    async def pause_command(self, ctx):
        player = self.get_player(ctx)
        if player.is_paused:
            raise PlayerIsAlreadyPaused
        if player.queue.is_empty:
           raise QueueIsEmpty
        try:
           await player.set_pause(True)
           embed=discord.Embed(title="Paused the song.", color=discord.Colour.magenta())
           await ctx.reply(embed=embed, mention_author=False)
        except:
          pass
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Paused song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
         embed=discord.Embed(title="The song is already paused.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)     
        elif isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
         
    @commands.command(name="resume")
    async def resume_command(self, ctx):
        player = self.get_player(ctx)
        if not player.is_paused:
            raise PlayerIsAlreadyPaused
        if player.queue.is_empty:
           raise QueueIsEmpty
        try:
          await player.set_pause(False)
          embed=discord.Embed(title="Resuming the song.", color=discord.Colour.orange())
          await ctx.reply(embed=embed, mention_author=False)
        except:
          pass
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Resumed song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @resume_command.error
    async def resume_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
         embed=discord.Embed(title="The song is already paused.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)     
        elif isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="stop")
    async def stop_command(self, ctx):
        player = self.get_player(ctx)
        if player.queue.is_empty:
          raise QueueIsEmpty
        await player.stop()
        embed=discord.Embed(title="Stopped the song.", color=discord.Colour.red())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Stopped song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @stop_command.error
    async def stop_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)	
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        
    @commands.command(name="clear")
    async def clear_command(self, ctx):
        player = self.get_player(ctx)
        if player.queue.is_empty:
          raise QueueIsEmpty
        await player.stop()
        player.queue.empty()
        embed=discord.Embed(title="Cleared the queue.", color=discord.Colour.dark_red())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Emptied queue in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @clear_command.error
    async def clear_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty!", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)	
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        
    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx):
        player = self.get_player(ctx)
        if not player.queue.upcoming:
            raise NoMoreTracks
        await player.stop()
        embed=discord.Embed(title="Skipping to the next track.", color=discord.Colour.dark_orange())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Skipping song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @next_command.error
    async def next_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoMoreTracks): 
            embed=discord.Embed(title=f"There are no more tracks left in the queue.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="previous")
    async def previous_command(self, ctx):
        player = self.get_player(ctx)
        if not player.queue.history:
            raise NoPreviousTracks
        player.queue.position -= 2
        await player.stop()
        embed=discord.Embed(title="Playing the previous track.", color=discord.Colour.blurple())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Playing previous track in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
          
    @previous_command.error
    async def previous_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoPreviousTracks):
            embed=discord.Embed(title=f"There are no previous tracks in the queue.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="shuffle")
    async def shuffle_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.shuffle()
        embed=discord.Embed(title=f"Shuffled the queue.", color=discord.Colour.random())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Shuffling queue in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @shuffle_command.error
    async def shuffle_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="loop")
    async def repeat_command(self, ctx, mode: str):
        if mode not in ("stop", "song", "queue"):
            raise InvalidRepeatMode
        player = self.get_player(ctx)

        if not player.is_playing:
            raise PlayerIsAlreadyPaused
        if mode == "stop":
          player = self.get_player(ctx)
          player.queue.set_repeat_mode("stop")
          embed=discord.Embed(title=f"Stopped the loop.", color=discord.Colour.dark_teal())
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(926147126180855850)
          embed=discord.Embed(description=f"Looped stopped in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
        if mode == "song":
          player = self.get_player(ctx)
          player.queue.set_repeat_mode("song")
          embed=discord.Embed(title=f"Looping the song.", color=discord.Colour.dark_teal())
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(926147126180855850)
          embed=discord.Embed(description=f"Looping song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
        if mode == "queue":
          player = self.get_player(ctx)
          player.queue.set_repeat_mode("queue")
          embed=discord.Embed(title=f"Looping the queue.", color=discord.Colour.dark_teal())
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(926147126180855850)
          embed=discord.Embed(description=f"Looping queue in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
          
    @repeat_command.error
    async def repeat_command_error(self,ctx,exc):
      if isinstance(exc, commands.MissingRequiredArgument):
        embed=discord.Embed(title="Loop options", color=discord.Colour.red())
        embed.add_field(name="niko loop stop", value="Stops the loop.", inline=False)
        embed.add_field(name="niko loop song", value="Loops the currently playing song.", inline=False)
        embed.add_field(name="niko loop queue", value="Loops every song in the queue.", inline=False)
        await ctx.reply(embed=embed, mention_author=False) 
      elif isinstance(exc, PlayerIsAlreadyPaused):
         embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
      elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="queue")
    async def queue_command(self, ctx, show: t.Optional[int] = 20):
        player = self.get_player(ctx)
        if player.queue.is_empty:
            raise QueueIsEmpty
        embed = discord.Embed(
            colour=discord.Colour.blue()
        )
        embed.add_field(name="Currently playing", value=getattr(player.queue.current_track, f"title", "Sorry, no tracks are currently playing!"), inline=False)
       	if upcoming := player.queue.upcoming:
          embed.add_field(
                name="Upcoming",
                value=(
                  "\n".join(	
                      f"**{i + 1}. **{t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                      for i, t in enumerate(upcoming[:show])
                 )
              ),
            )
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
        print(f'{player.queue.current_track.author} {player.queue.current_track.title}')
        results = sp.search(q=f'{player.queue.current_track.author} {player.queue.current_track.title}', limit=1)
        for idx, track in enumerate(results['tracks']['items']):
            querytrack = track['name']
            queryartist = track["artists"][0]["name"]	
        try:
           embed.set_thumbnail(url=f"{track['album']['images'][0]['url']}")
        except:
           pass
        await ctx.reply(embed=embed, mention_author=False)
	
    @queue_command.error
    async def queue_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)

    @commands.group(name="volume", invoke_without_command=True, aliases=["vol"])
    async def volume_group(self, ctx, volume: int):
        player = self.get_player(ctx)
        if volume < 0:
            raise VolumeTooLow
        if volume > 150:
            raise VolumeTooHigh
        await player.set_volume(volume)
        embed=discord.Embed(title=f"The volume is now at **{volume:,}**%", color=discord.Colour.darker_grey())
        await ctx.reply(embed=embed, mention_author=False)
        
    @volume_group.error
    async def volume_group_error(self, ctx, exc):
        if isinstance(exc, VolumeTooLow):
         embed=discord.Embed(title=f"The volume must be higher than **0**%", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, VolumeTooHigh):
         embed=discord.Embed(title=f"The volume must be less than **150**%", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(title=f"Volume options", color=discord.Colour.red())
           embed.add_field(name="niko volume up", value="Increases the volume by 10%", inline=False)
           embed.add_field(name="niko volume down", value="Decreases the volume by 10%", inline=False)
           await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        
    @volume_group.command(name="up", aliases=["Up"])
    async def volume_up_command(self, ctx):
        player = self.get_player(ctx)
        if player.volume == 150:
            raise MaxVolume
        await player.set_volume(value := min(player.volume + 10, 150))
        
    @volume_up_command.error
    async def volume_up_command_error(self, ctx, exc):
        if isinstance(exc, MaxVolume):
            embed=discord.Embed(title=f"The volume is already at the max level (150%)", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)

    @volume_group.command(name="down", aliases=["Down"])
    async def volume_down_command(self, ctx):
        player = self.get_player(ctx)

        if player.volume == 0:
            raise MinVolume

        await player.set_volume(value := max(0, player.volume - 10))

    @volume_down_command.error
    async def volume_down_command_error(self, ctx, exc):
        if isinstance(exc, MinVolume):
            embed=discord.Embed(title=f"The volume is already at the minimum level (0%)", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="playing", aliases=["np", "nowplaying"])
    async def playing_command(self, ctx):
                player = self.get_player(ctx)
                if not player.is_playing:
                   raise PlayerIsAlreadyPaused
                sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
                results = sp.search(q=f'{player.queue.current_track.author} {player.queue.current_track.title}', limit=1)
                for idx, track in enumerate(results['tracks']['items']):
                 querytrack = track['name']
                 queryartist = track["artists"][0]["name"]	
                embed=discord.Embed(title="Now Playing",color=discord.Colour.teal())
                try:
                  embed.add_field(name="Name", value=f"{querytrack}", inline=False)
                except:
                  embed.add_field(name="Name", value=f"{player.queue.current_track.title}", inline=False)
                try:
                  embed.add_field(name="Artist", value=f"{queryartist}", inline=False)
                except:
                  embed.add_field(name="Artist", value=f"{player.queue.current_track.author}", inline=False)
                try:
                  embed.add_field(name="Album", value=f"{track['album']['name']}", inline=False)
                except:
                  pass
                position = divmod(player.position, 60000)
                length = divmod(player.queue.current_track.length, 60000)
                embed.add_field(
                  name="Duration Played",
                  value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}",
                  inline=False
                 )
                try:
                  embed.add_field(name="Release Date", value=f"{track['album']['release_date']}", inline=False)
                except:
                  pass
                try:
                  embed.set_thumbnail(url=f"{track['album']['images'][0]['url']}")
                except:
                  pass
                await ctx.reply(embed=embed, mention_author=False)

    @playing_command.error
    async def playing_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            embed=discord.Embed(title=f"There is no song currently playing at the moment.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="skipto", aliases=["goto"])
    async def skipto_command(self, ctx, index: int):
        player = self.get_player(ctx)
        if player.queue.is_empty:
            raise QueueIsEmpty
        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks	
        player.queue.position = index - 1
        await player.stop()
        embed=discord.Embed(title=f"Playing track in position **{index}**", color=discord.Colour.dark_green())
        await ctx.reply(embed=embed, mention_author=False)

    @skipto_command.error
    async def skipto_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
         embed=discord.Embed(title=f"The queue is currently empty", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoMoreTracks):
         embed=discord.Embed(title=f"Invalid position entered.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
         
    @commands.command(name="remove", aliases=["rm"])
    async def remove_command(self, ctx, index: int):
        player = self.get_player(ctx)
        if player.queue.is_empty:
            raise QueueIsEmpty
        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks	
        embed=discord.Embed(title=f"Removed track in position {index}.", color=discord.Colour.dark_green())
        await ctx.reply(embed=embed, mention_author=False)
        del(player.queue._queue[index])

    @remove_command.error
    async def remove_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
         embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoMoreTracks):
         embed=discord.Embed(title=f"Invalid position entered.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="replay", aliases=["rep"])
    async def restart_command(self, ctx):
        player = self.get_player(ctx)
        if player.queue.is_empty:
            raise QueueIsEmpty
        await player.seek(0)
        embed=discord.Embed(title=f"Replaying the song.", color=discord.Colour.dark_purple())
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(926147126180855850)
        embed=discord.Embed(description=f"Replaying song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @restart_command.error
    async def restart_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
          embed=discord.Embed(title=f"There queue is currently empty.", color=discord.Colour.red())
          await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="seek", aliases=["sek"])
    async def seek_command(self, ctx, position: str):
        player = self.get_player(ctx)
        if player.queue.is_empty:
            raise QueueIsEmpty
        if not (match := re.match(TIME_REGEX, position)):
            raise InvalidTimeString
        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))
        await player.seek(secs * 1000)
        embed=discord.Embed(title=f"Seeked the song.", color=discord.Colour.dark_gray())
        await ctx.reply(embed=embed, mention_author=False)
        
    @seek_command.error
    async def seek_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
         embed=discord.Embed(title=f"The queue is currently empty.", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        if isinstance(exc, InvalidTimeString):
         embed=discord.Embed(title=f"Invalid time entered", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(title=f"You have not joined a voice channel.", color=discord.Colour.red())
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="lyrics")
    async def lyrics_command(self, ctx, *, title):
     genius = lyricsgenius.Genius("GENIUS API KEY")
     genius.verbose = False
     genius.remove_section_headers = True
     genius.skip_non_songs = True
     song = genius.search_song(f"{title}")
     test_stirng = f"{song.lyrics}"
     total = 1
     for i in range(len(test_stirng)):
       if(test_stirng[i] == ' ' or test_stirng == '\n' or test_stirng == '\t'):
         total = total + 1
     if total > 600:
       embed=discord.Embed(title="Character Limit Exceeded", description=f"The lyrics in this song are too long. (Over 6000 characters)", color=discord.Colour.red())
       await ctx.reply(embed=embed, mention_author=False)
     sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
     results = sp.search(q=f'{title}', limit=1)
     for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]
        queryfinal =f"{queryartist}" + " " + f"{querytrack}"
     embed2=discord.Embed(title=f"{querytrack}" ,description=f"{song.lyrics}")
     await ctx.reply(embed=embed2, mention_author=False)

    @lyrics_command.error
    async def lyrics_command_error(self, ctx, exc):
        if isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(title=f"What song's lyrics would you like?", color=discord.Colour.red())
           await ctx.reply(embed=embed, mention_author=False)
           
  
    @commands.command(name="eq", aliases=["equalizer"])
    async def eq_command(self, ctx, preset: str):
        player = self.get_player(ctx)
        eq = getattr(wavelink.eqs.Equalizer, preset, None)
        if not eq:
            raise InvalidEQPreset
        await player.set_eq(eq())
        embed=discord.Embed(title=f"Equalizer set to the **{preset}** preset.", color=discord.Colour.default())
        await ctx.reply(embed=embed, mention_author=False)

    @eq_command.error
    async def eq_command_error(self, ctx, exc):
        if isinstance(exc, InvalidEQPreset):
           embed=discord.Embed(title=f"Equalizer presets", color=discord.Colour.red())
           embed.add_field(name="niko eq flat", value="Flattens most sounds in a song/video.", inline=False)
           embed.add_field(name="niko eq boost", value="Makes every sound in a song/video louder.", inline=False)
           embed.add_field(name="niko eq metal", value="Lets select instruments related to metal louder.", inline=False)
           embed.add_field(name="niko eq piano", value="Makes the sounds of pianos in a song/video louder.", inline=False)
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(title=f"Equalizer presets!", color=discord.Colour.red())
           embed.add_field(name="niko eq flat", value="Flattens most sounds in a song/video.", inline=False)
           embed.add_field(name="niko eq boost", value="Makes every sound in a song/video louder.", inline=False)
           embed.add_field(name="niko eq metal", value="Lets select instruments related to metal louder.", inline=False)
           embed.add_field(name="niko eq piano", value="Makes the sounds of pianos in a song/video louder.", inline=False)
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
        
    @commands.command(name="invite", aliases=["inv"])
    async def invite(self, ctx):
     embed=discord.Embed(description="Related links.", color=discord.Colour.purple())
     await ctx.reply(
           embed=embed,
        components = [
        [
            Button(label = "Invite me!", custom_id = "button1", style=5, url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands"),
            Button(label = "Vote for me!", custom_id = "button1", style=5, url="https://top.gg/bot/915595163286532167/vote"),
            Button(label = "Visit my project!", custom_id = "button1", style=5, url="https://github.com/ZingyTomato/Niko-Music"),
            Button(label = "Support server!", custom_id = "button1", style=5, url="https://discord.gg/grSvEPYtDF")
        ]
        ],
           mention_author=False
    )
    
    @commands.command(name="vote", aliases=["vt"])
    async def vote(self, ctx):
     embed=discord.Embed(description="Vote for me!", color=discord.Colour.purple())
     await ctx.reply(
           embed=embed,
        components = [
        [
            Button(label = "Click here to vote for me!", custom_id = "button1", style=5, url="https://top.gg/bot/915595163286532167/vote"),
        ]
        ],
           mention_author=False
    )
          
    @commands.command(name="help", aliases=["h"])
    async def help(self, ctx):
          embed=discord.Embed(title="Help Center",description="Here's a list of all my commands.", color=discord.Colour.gold())
          embed.add_field(name = "@Niko Music play", value = "Niko plays any song you want.")
          embed.add_field(name = "@Niko Music join", value = "Niko joins your VC.")
          embed.add_field(name = "@Niko Music leave", value = "Niko leaves your VC.")
          embed.add_field(name = "@Niko Music pause", value = "Niko pauses the song.")
          embed.add_field(name = "@Niko Music resume", value = "Niko resumes the song.")
          embed.add_field(name = "@Niko Music loop", value = "Niko loops your requested song.")
          embed.add_field(name = "@Niko Music seek", value = "Niko move ahead in the song based on the time provided.")
          embed.add_field(name = "@Niko Music queue", value = "Niko shows you the queue.")
          embed.add_field(name = "@Niko Music skip", value = "Niko skips the currently playing song")
          embed.add_field(name = "@Niko Music goto", value = "Niko plays a track from the queue based on an integer.")
          embed.add_field(name = "@Niko Music volume", value = "Niko changes the volume.")
          embed.add_field(name = "@Niko Music np", value = "Niko shows the currently playing song.")
          embed.add_field(name = "@Niko Music shuffle", value = "Niko plays a random song from the queue.")
          embed.add_field(name = "@Niko Music stop", value = "Niko stops the song.")
          embed.add_field(name = "@Niko Music clear", value = "Niko empties the queue.")
          embed.add_field(name = "@Niko Music lyrics", value = "Niko finds lyrics on most songs!")
          embed.add_field(name = "@Niko Music eq help", value = "Niko changes the song filter based on a set of presets!")
          embed.add_field(name = "@Niko Music replay", value = "Niko rewinds the song from the start.")
          embed.add_field(name = "@Niko Music recommend", value = "Niko plays 10 recommended songs based on what's playing!")
          embed.add_field(name = "@Niko Music remove", value = "Niko removes a track from the queue based on an integer.")
          embed.add_field(name = "@Niko Music invite", value = "Invite Niko to other servers!")
          embed.set_footer(text="Made by ZingyTomato#0604. DM if you face any issues.")
          await ctx.reply(embed=embed,components = [[Button(label = "Invite me!", custom_id = "button1", style=5, url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands"),Button(label = "Vote for me!", custom_id = "button1", style=5, url="https://top.gg/bot/915595163286532167/vote"),Button(label = "Visit my project!", custom_id = "button1", style=5, url="https://github.com/ZingyTomato/Niko-Music"), Button(label = "Support Server!", custom_id = "button1", style=5, url="https://discord.gg/grSvEPYtDF")]],mention_author=False)
    
def setup(bot):
    bot.add_cog(Music(bot))
