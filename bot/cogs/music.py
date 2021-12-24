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
from discord_components import DiscordComponents, ComponentsBot, Button, Select, SelectOption
from discord import Webhook, AsyncWebhookAdapter
from discord_slash import cog_ext, SlashContext, SlashCommand
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


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
        self.position = 100

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
        if not tracks:
            embed=discord.Embed(description="Sorry, I couldn't find any songs with that title! Make sure to include the artists name as well.", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)

        elif len(f"{tracks}".split('\n'))== 1:
            self.queue.add(tracks[0])
            embed=discord.Embed(description=f":notes: **{tracks[0].title}** has been added to the queue!", color=discord.Colour.green())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text="Check the current queue with `niko queue`")
            await ctx.reply(embed=embed, mention_author=False)
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
                "host": "lavalink.devz.cloud",
                "port": 443,
                "rest_uri": "https://lavalink.devz.cloud",
                "password": "mathiscool",
                "identifier": "MAIN",
                "region": "us_central",
                "secure": True,
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
        await ctx.guild.change_voice_state(channel = ctx.message.author.voice.channel, self_mute=False, self_deaf=True)
        chanid = ctx.author.voice.channel.id
        embed=discord.Embed(description=f":wave: I have just **joined** <#{chanid}>", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Joined VC in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
            
    @commands.command(name="disconnect", aliases=["leave"])
    async def disconnect_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await player.teardown()
        embed=discord.Embed(description=f":wave: I have just **left** your VC!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Left VC in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @disconnect_command.error
    async def disconnect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            embed=discord.Embed(description=f":no_entry_sign: Sorry, you are already **in** a voice channel.", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(description=f":no_entry_sign: Sorry, you are not currently **in** a voice channel.", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        
            
    @commands.command(name="play",pass_context=True)	
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await ctx.guild.change_voice_state(channel=ctx.message.author.voice.channel, self_mute=False, self_deaf=True)

        query = query.strip("<>")
        if "youtube" in query:
          embed=discord.Embed(description=":no_entry_sign: **Supported** Platforms: Soundcloud (With Search functionality), Spotify (Link only), Bandcamp (Link only), Vimeo (Link only), Twitch (Link only), HTTP Streams (Link only) and local files.", color=discord.Colour.red())
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
          query = f"scsearch:{queryfinal}"
          await player.add_tracks(ctx, await self.wavelink.get_tracks(query))	
        if "https://open.spotify.com/album" in query:	
         sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
         album_link = f"{query}"
         album_id= album_link.split("/")[-1].split("?")[0]
         for track in sp.album_tracks(album_id)["items"]:
          track_name = track["name"]
          track_artist = track["artists"][0]["name"]
          queryfinal = f"{track_name} " + " " + f"{track_artist}" 
          query = f"scsearch:{queryfinal}"
          await player.add_tracks(ctx, await self.wavelink.get_tracks(query))	
        if "https://deezer.com" in query:
          embed=discord.Embed(description=":no_entry_sign: **Supported** Platforms: Soundcloud (With Search functionality), Spotify Playlists and Albums (Link only), Bandcamp (Link only), Vimeo (Link only), Twitch (Link only), HTTP Streams (Link only) and local files.", color=discord.Colour.red())
          return await ctx.reply(embed=embed, mention_author=False)
           
        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="SPOT CLIENT ID",client_secret="SPOT CLIENT SECRET"))
                results = sp.search(q=f'{query}', limit=1)
                for idx, track in enumerate(results['tracks']['items']):
                  querytrack = track['name']
                  queryartist = track["artists"][0]["name"]
                  queryfinal = f"{querytrack}" + " " +  f"{queryartist}"
                  print(queryfinal)
                  querysearch = f"scsearch:{queryfinal}"
            await player.add_tracks(ctx, await self.wavelink.get_tracks(querysearch))	
            if player.queue.current_track.length == 30000:
                embed=discord.Embed(description=":no_entry_sign: Sorry! This song is currently blocked in my region by soundcloud :pensive:", color=discord.Colour.red())
                await ctx.reply(embed=embed, mention_author=False)
                await player.stop()
            channel = self.bot.get_channel(918347985937645609)
            embed=discord.Embed(description=f"``{ctx.author.name}`` is playing ``{player.queue.current_track.title}`` by ``{player.queue.current_track.author}`` in ``{ctx.message.guild.name}`` which is ``{player.queue.current_track.length}`` seconds long!")
            await channel.send(embed=embed)
            
    @play_command.error
    async def play_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text="Tip : You can add a song to the queue by playing a song by typing `niko play songname`")
            await ctx.reply(embed=embed, mention_author=False)	
        elif isinstance(exc, NoVoiceChannel):
            embed=discord.Embed(description=f":no_entry_sign: Sorry, you are not currently **in** a voice channel.", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="pause")
    async def pause_command(self, ctx):
        player = self.get_player(ctx)
        if player.is_paused:
            raise PlayerIsAlreadyPaused
        await player.set_pause(True)
        embed=discord.Embed(description=":pause_button: I've just **paused** the song!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Paused song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
         embed=discord.Embed(description=":pause_button: Sorry, the song is already **paused**!", color=discord.Colour.red())
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)     


    @commands.command(name="resume")
    async def resume_command(self, ctx):
        player = self.get_player(ctx)
        if not player.is_paused:
            raise PlayerIsAlreadyPaused
        await player.set_pause(False)
        embed=discord.Embed(description=":play_pause: I've just **resumed** the song!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Resumed song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @commands.command(name="stop")
    async def stop_command(self, ctx):
        player = self.get_player(ctx)
        await player.stop()
        player.queue.empty()
        embed=discord.Embed(description=":no_entry_sign: I've just **stopped** the currently playing song!", color=discord.Colour.red())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Stopped song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        
    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx):
        player = self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks

        await player.stop()
        embed=discord.Embed(description=":play_pause: I'm now playing the **next** song in the queue!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Tip : You can check the current queue with `niko queue`")
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Skipping song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        if player.queue.current_track.length == 30000:
         embed=discord.Embed(description=":no_entry_sign: Sorry! This song is currently blocked in my region by soundcloud :pensive:", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
         await player.stop()

        
    @next_command.error
    async def next_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text="Tip : You can add a song to the queue by playing a song by typing `niko play songname`")	
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoMoreTracks): 
            embed=discord.Embed(description=f":no_entry_sign: Sorry! There are no more **tracks** in the queue!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="previous")
    async def previous_command(self, ctx):
        player = self.get_player(ctx)
        if not player.queue.history:
            raise NoPreviousTracks
        player.queue.position -= 2
        await player.stop()
        embed=discord.Embed(description=":rewind: I'm playing the **previous** song in the queue!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Tip : You can check the current queue by typing `niko queue`")
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Playing previous track in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)
        if player.queue.current_track.length == 30000:
         embed=discord.Embed(description=":no_entry_sign: Sorry! This song is currently blocked in my region by soundcloud :pensive:", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
         await player.stop()
          
    @previous_command.error
    async def previous_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently**empty**!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text="Tip : You can add a song to the queue by playing a song by typing `niko play songname`")	
            await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoPreviousTracks):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! There are no **previous** tracks in the queue!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="shuffle")
    async def shuffle_command(self, ctx):
        player = self.get_player(ctx)
        player.queue.shuffle()
        embed=discord.Embed(description=f"**Shuffled** the queue!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_footer(text="Tip : You can check the new queue with `niko queue`")
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Shuffling queue in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @shuffle_command.error
    async def shuffle_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            embed.set_footer(text="Tip : You can add a song to the queue by playing a song by typing `niko play songname`")	
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
          embed=discord.Embed(description=f":no_entry_sign: I've just **stopped** the loop!", color=discord.Colour.red())
          embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
          embed.set_footer(text="Available options for loop  are : `stop, song and queue`")
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(918347985937645609)
          embed=discord.Embed(description=f"Looped stopped in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
        if mode == "song":
          player = self.get_player(ctx)
          player.queue.set_repeat_mode("song")
          embed=discord.Embed(description=f":loop: I'm now looping the **currently** playing song!", color=discord.Colour.green())
          embed.set_footer(text="Available options for loop are : stop, song and queue")
          embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(918347985937645609)
          embed=discord.Embed(description=f"Looping song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
        if mode == "queue":
          player = self.get_player(ctx)
          player.queue.set_repeat_mode("queue")
          embed=discord.Embed(description=f":loop: I'm now looping the **queue**!", color=discord.Colour.green())
          embed.set_footer(text="Available options for loop are : stop, song and queue")
          embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
          await ctx.reply(embed=embed, mention_author=False)
          channel = self.bot.get_channel(918347985937645609)
          embed=discord.Embed(description=f"Looping queue in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
          await channel.send(embed=embed)
          
    @repeat_command.error
    async def repeat_command_error(self,ctx,exc):
      if isinstance(exc, commands.MissingRequiredArgument):
        embed=discord.Embed(description="Here are the available **loop** options.", color=discord.Colour.red())
        embed.add_field(name="🚫️ niko loop stop", value="Stops the loop.", inline=False)
        embed.add_field(name=":loop: niko loop song", value="Loops the currently playing song.", inline=False)
        embed.add_field(name=":loop: niko loop queue", value="Loops every song in the queue.", inline=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False) 
      elif isinstance(exc, PlayerIsAlreadyPaused):
         embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
         embed.set_footer(text="Tip: You can add a song to the queue with `niko play songname`")
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
          
    @commands.command(name="queue")
    async def queue_command(self, ctx, show: t.Optional[int] = 10):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        embed = discord.Embed(
            title="The Queue",
            description=f"Here are the next **{show}** tracks.",
            colour=discord.Colour.green()
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name=":notes: Currently playing!", value=getattr(player.queue.current_track, "title", "Sorry, no tracks are currently **playing** at the moment!"), inline=False)
        if upcoming := player.queue.upcoming:
            embed.add_field(
                name=":eyes: What's next",
                value="\n".join(t.title for t in upcoming[:show]),
                inline=False
            )
        msg = await ctx.reply(embed=embed, mention_author=False)
	
    @queue_command.error
    async def queue_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
            embed.set_footer(text="Tip : You can add a song to the queue by playing a song with `niko play songname`!")	
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)


    @commands.group(name="volume", invoke_without_command=True)
    async def volume_group(self, ctx, volume: int):
        player = self.get_player(ctx)

        if volume < 0:
            raise VolumeTooLow

        if volume > 150:
            raise VolumeTooHigh

        await player.set_volume(volume)
        embed=discord.Embed(description=f":loud_sound: I've just set the volume to **{volume:,}**%", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        
    @volume_group.error
    async def volume_group_error(self, ctx, exc):
        if isinstance(exc, VolumeTooLow):
         embed=discord.Embed(description=f":loud_sound: Sorry! The volume must be higher than **0**%", color=discord.Colour.red())
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, VolumeTooHigh):
         embed=discord.Embed(description=f":loud_sound: Sorry! The volume must be less than **150**%", color=discord.Colour.red())
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(title=f":speaker: Volume options!", color=discord.Colour.red())
           embed.add_field(name=":loudspeaker: up", value="Increases the volume by 10%", inline=False)
           embed.add_field(name=":mute: down", value="Decreases the volume by 10%", inline=False)
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
        
    @volume_group.command(name="up")
    async def volume_up_command(self, ctx):
        player = self.get_player(ctx)

        if player.volume == 150:
            raise MaxVolume

        await player.set_volume(value := min(player.volume + 10, 150))
        
    @volume_up_command.error
    async def volume_up_command_error(self, ctx, exc):
        if isinstance(exc, MaxVolume):
            embed=discord.Embed(description=f":sound: Sorry! The volume is already at the **max** level (150%)", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)

    @volume_group.command(name="down")
    async def volume_down_command(self, ctx):
        player = self.get_player(ctx)

        if player.volume == 0:
            raise MinVolume

        await player.set_volume(value := max(0, player.volume - 10))

    @volume_down_command.error
    async def volume_down_command_error(self, ctx, exc):
        if isinstance(exc, MinVolume):
            embed=discord.Embed(description=f":sound: Sorry! The volume is already at the **minimum** level (0%)", color=discord.Colour.red())
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="playing", aliases=["np"])
    async def playing_command(self, ctx):
        player = self.get_player(ctx)

        if not player.is_playing:
            raise PlayerIsAlreadyPaused

        embed = discord.Embed(
            title=":notes: Currently playing!",
            colour=discord.Colour.green(),
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.add_field(name=":scroll: Title", value=player.queue.current_track.title, inline=False)
        embed.add_field(name=":blond_haired_person: Artist", value=player.queue.current_track.author, inline=False)

        position = divmod(player.position, 60000)
        length = divmod(player.queue.current_track.length, 60000)
        embed.add_field(
            name=":alarm_clock: Duration Played",
            value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}",
            inline=False
        )

        await ctx.reply(embed=embed, mention_author=False)

    @playing_command.error
    async def playing_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            embed=discord.Embed(description=f":no_entry_sign: Sorry! There is no song currently **playing** at the moment!", color=discord.Colour.red())
            embed.set_footer(text="Tip: You can play a song with `niko play songname`")
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="skipto", aliases=["goto"])
    async def skipto_command(self, ctx, index: int):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks

        player.queue.position = index - 2
        await player.stop()
        embed=discord.Embed(description=f":notes: I'm playing the track in position **{index}**", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        if player.queue.current_track.length == 30000:
         embed=discord.Embed(description=":no_entry_sign: Sorry! This song is currently blocked in my region by soundcloud :pensive:", color=discord.Colour.red())
         await ctx.reply(embed=embed, mention_author=False)
         await player.stop()

    @skipto_command.error
    async def skipto_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
         embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
         embed.set_footer(text="Tip: You can add a song to the queue with `niko play songname`")
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, NoMoreTracks):
         embed=discord.Embed(description=f":no_entry_sign: Sorry! That position does not **exist**!", color=discord.Colour.red())
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="replay")
    async def restart_command(self, ctx):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        await player.seek(0)
        embed=discord.Embed(description=f"I'm **replaying** the currently playing song!", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        channel = self.bot.get_channel(918347985937645609)
        embed=discord.Embed(description=f"Replaying song in `{ctx.message.guild.name}`. Requested by `{ctx.author.name}`")
        await channel.send(embed=embed)

    @restart_command.error
    async def restart_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
          embed=discord.Embed(description=f":no_entry_sign: Sorry! There are no **song** currently playing at the moment!", color=discord.Colour.red())
          embed.set_footer(text="Tip: You can add play a song by typing `niko play songname`")
          embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
          await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="seek")
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
        embed=discord.Embed(description=f"I've just **Seeked** the song to your desired position!", color=discord.Colour.red())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        
    @seek_command.error
    async def seek_command_error(self, ctx, exc):
        if isinstance(exc, QueueIsEmpty):
         embed=discord.Embed(description=f":no_entry_sign: Sorry! The queue is currently **empty**!", color=discord.Colour.red())
         embed.set_footer(text="Tip: You can add a song to the queue by typing `niko play songname`")
         embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
         await ctx.reply(embed=embed, mention_author=False)
            
    @commands.command(name="lyrics")
    async def lyrics_command(self, ctx, *, title):
     genius = lyricsgenius.Genius("GENIUS API KEY")
     genius.verbose = False
     genius.remove_section_headers = True
     genius.skip_non_songs = True
     song = genius.search_song(f"{title}")
     test_stirng = f"{song.lyrics}"
     embed1=discord.Embed(description=":mag: Searching for lyrics... please wait!")
     msg = await ctx.reply(embed=embed1, mention_author=False)
     total = 1
     for i in range(len(test_stirng)):
       if(test_stirng[i] == ' ' or test_stirng == '\n' or test_stirng == '\t'):
         total = total + 1
     if total > 600:
       embed=discord.Embed(description=f":no_entry_sign: Sorry! The number of characters in **{title}** exceeds Discord's character limit! (6000 characters). There's nothing I can do :pensive: ", color=discord.Colour.red())
       embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
       await asyncio.sleep(1)
       await msg.edit(embed=embed)
     await asyncio.sleep(3)
     embed2=discord.Embed(title=f"📜 Lyrics for **{title}**!" ,description=f"{song.lyrics}")
     embed2.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
     await msg.edit(embed=embed2)
  
    @lyrics_command.error
    async def lyrics_command_error(self, ctx, exc):
        if isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(description=f":no_entry_sign: What song's **lyrics** would you like to see?", color=discord.Colour.red())
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
  
    @commands.command(name="eq")
    async def eq_command(self, ctx, preset: str):
        player = self.get_player(ctx)

        eq = getattr(wavelink.eqs.Equalizer, preset, None)
        if not eq:
            raise InvalidEQPreset

        await player.set_eq(eq())
        embed=discord.Embed(description=f"I've just set the Equaliser to the **{preset}** preset.", color=discord.Colour.green())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)

    @eq_command.error
    async def eq_command_error(self, ctx, exc):
        if isinstance(exc, InvalidEQPreset):
           embed=discord.Embed(title=f"🔊️ Here are the available equalizer presets!", color=discord.Colour.red())
           embed.add_field(name="🫓️ flat", value="Flattens most sounds in a song/video.", inline=False)
           embed.add_field(name="💥️ boost", value="Makes every sound in a song/video louder.", inline=False)
           embed.add_field(name="🎸️ metal", value="Lets select instruments related to metal louder.", inline=False)
           embed.add_field(name="🎹️ piano", value="Makes the sounds of pianos in a song/video louder.", inline=False)
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
        elif isinstance(exc, commands.MissingRequiredArgument):
           embed=discord.Embed(title=f"🔊️ Here are the available equalizer presets!", color=discord.Colour.red())
           embed.add_field(name="🫓️ flat", value="Flattens most sounds in a song/video.", inline=False)
           embed.add_field(name="💥️ boost", value="Makes every sound in a song/video louder.", inline=False)
           embed.add_field(name="🎸️ metal", value="Lets select instruments related to metal louder.", inline=False)
           embed.add_field(name="🎹️ piano", value="Makes the sounds of pianos in a song/video louder.", inline=False)
           embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
           await ctx.reply(embed=embed, mention_author=False)
        
    @commands.command(name="invite")
    async def invite(self, ctx):
      buttons = [
    create_button(style=5, label="📩 Invite me!", url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands"),
]
      action_row = create_actionrow(*buttons)
      embed=discord.Embed(description=":wave:  Click the button below to **invite** me to other servers!")
      await ctx.reply(embed=embed, components=[action_row], mention_author=False)
          
    @commands.command(name="help")
    async def help(self, ctx):
          embed=discord.Embed(title=":hospital: Help Center",description="Here's a list of all my commands.", color=discord.Colour.green())
          embed.add_field(name = ":notes: niko play", value = "Niko play any song you want.")
          embed.add_field(name = ":lock: niko join", value = "Niko joins your VC.")
          embed.add_field(name = "🔓niko leave", value = "Niko leaves your VC.")
          embed.add_field(name = "⏸️ niko pause", value = "Niko pauses the song.")
          embed.add_field(name = "▶️ niko resume", value = "Niko resumes the song.")
          embed.add_field(name = ":repeat: niko loop", value = "Niko loops your requested song.")
          embed.add_field(name = ":eyes: niko seek", value = "Niko move ahead in the song based on the time provided.")
          embed.add_field(name = " :scroll: niko queue", value = "Niko shows you the queue.")
          embed.add_field(name = " ❌️ niko skip", value = "Niko skips the currently playing song")
          embed.add_field(name = " 👆️ niko goto", value = "Niko plays a track from the queue based on an integer.")
          embed.add_field(name = " 🔊️ niko volume", value = "Niko changes the volume.")
          embed.add_field(name = " :alarm_clock:  niko np", value = "Niko shows the currently playing song.")
          embed.add_field(name = "🃏️ niko shuffle", value = "Niko plays a random song from the queue.")
          embed.add_field(name = "🛑 niko stop", value = "Niko stops the song.")
          embed.add_field(name = ":abc: niko lyrics", value = "Niko finds lyrics on most songs!")
          embed.add_field(name = ":loudspeaker: niko eq help", value = "Niko changes the song filter based on a set of presets!")
          embed.add_field(name = ":rewind: niko replay", value = "Niko rewinds the song from the start.")
          embed.add_field(name = "📩 niko invite", value = "Invite niko to other servers!")
          await ctx.send(embed=embed)
    
def setup(bot):
    bot.add_cog(Music(bot))
