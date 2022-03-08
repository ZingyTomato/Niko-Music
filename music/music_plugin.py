import logging
from typing import Optional
import hikari
import lightbulb
import lavasnek_rs
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import lyricsgenius
import urllib.parse as urlparse
import os
import dotenv
import datetime
from datetime import date
import miru
from miru.ext import nav
import random
import asyncio

dotenv.load_dotenv()

HIKARI_VOICE = False
URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
TIME_REGEX = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"
SPOTCLIENT_ID=os.getenv("SPOTID")
SPOTCLIENT_SECRET=os.getenv("SPOTSECRET")
GENIUS_API_KEY=os.getenv("GENAPI")
TOKEN=os.getenv("TOKEN")
LAVALINK_SERVER="lavalink"
LAVALINK_PASSWORD="nikomusic"
LAVALINK_PORT=2333
LOGGING_CHANNEL=os.getenv("LOGGING_CHANNEL")

plugin = lightbulb.Plugin("Music", include_datastore = True)

class EventHandler:

    async def track_start(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackStart) -> None:
        guild_node = await lavalink.get_guild_node(event.guild_id)
        song = await plugin.d.lavalink.decode_track(event.track)
        chanid = guild_node.get_data().get("ChannelID")
        firsttrack = guild_node.get_data().get("First")
        recommend_enabled = guild_node.get_data().get("recommend")
        loop_enabled = guild_node.get_data().get("loop")
        embed=hikari.Embed(title="**Track Started**", description=f"**{song.title} - {song.author}** started on guild: {event.guild_id}", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
        results = sp.search(q=f"{song.author} {song.title}", limit=1)
        for idx, track in enumerate(results['tracks']['items']):
           querytrack = track['name']
        if firsttrack == False:
          if recommend_enabled:
            try:
              embed=hikari.Embed(title="**Recommended the next track.**", description=f"{[song.title]}({track['external_urls']['spotify']})", color=0x6100FF)
            except:
              embed=hikari.Embed(title="**Recommended the next track.**", description=f"**{song.title}** - **{song.author}**", color=0x6100FF)
          elif loop_enabled: 
            try:
              embed=hikari.Embed(title="**Playing the next track in the queueloop.**", description=f"{[song.title]}({track['external_urls']['spotify']})", color=0x6100FF)
            except:
              embed=hikari.Embed(title="**Playing the next track in the queueloop.**", description=f"**{song.title}** - **{song.author}**", color=0x6100FF)
          else:
            try:
              embed=hikari.Embed(title="**Playing the next track.**", description=f"{[song.title]}({track['external_urls']['spotify']})", color=0x6100FF)
            except:
              embed=hikari.Embed(title="**Playing the next track.**", description=f"**{song.title}** - **{song.author}**", color=0x6100FF)
          try:
             embed.add_field(name="Artist", value=f"{[song.author]}({track['artists'][0]['external_urls']['spotify']})", inline=False)
          except:
             embed.add_field(name="Artist", value=f"{song.author}", inline=False)
          try:
             embed.add_field(name="Album", value=f"{[track['album']['name']]}({track['album']['external_urls']['spotify']})", inline=False)
          except:
             pass
          try:
            embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
          except:
            pass
          resp = await plugin.bot.rest.create_message(chanid, embed=embed)
          await asyncio.sleep(30)
          await resp.delete()
        
    async def track_finish(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackFinish) -> None:
        BOT_ID = plugin.bot.application.id
        guild_node = await lavalink.get_guild_node(event.guild_id)
        states = plugin.bot.cache.get_voice_states_view_for_guild(event.guild_id)
        users = [state async for state in states.iterator().filter(lambda i: i.user_id != BOT_ID)]
        loop_enabled = guild_node.get_data().get("loop")
        recommend_enabled = guild_node.get_data().get("recommend")
        if not guild_node or not guild_node.now_playing and not users:
            await plugin.d.lavalink.destroy(event.guild_id)
            await plugin.d.lavalink.leave(event.guild_id)
            await plugin.d.lavalink.remove_guild_node(event.guild_id)
            await plugin.d.lavalink.remove_guild_from_loops(event.guild_id)
            return
        embed=hikari.Embed(title="**Track Finished**", description=f"Track finished on guild: {event.guild_id}", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        song = await plugin.d.lavalink.decode_track(event.track)
        if loop_enabled:
            track = f"{song.author}" + " " + f"{song.title}"
            result = f"ytmsearch:{track}"
            results = await plugin.d.lavalink.get_tracks(result)
            await lavalink.play(event.guild_id, results.tracks[0]).queue()
        if recommend_enabled:
            url_data = urlparse.urlparse(f"{song.uri}")
            query = urlparse.parse_qs(url_data.query)
            video = query["v"][0]
            ytmusic = YTMusic()
            playlist = ytmusic.get_watch_playlist(videoId=f"{video}", limit=1)
            song = playlist["tracks"][random.randrange(1,10)]["title"]
            recommended_track = f"ytmsearch:{song}"
            query_information = await lavalink.get_tracks(recommended_track)
            await lavalink.play(event.guild_id, query_information.tracks[0]).queue()

    async def track_exception(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackException) -> None:
        embed=hikari.Embed(title="**Issue**", description=f"There was an issue on guild: {event.guild_id}", color=0xC80000, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)

        skip = await lavalink.skip(event.guild_id)
        node = await lavalink.get_guild_node(event.guild_id)

        if not node:
            return

        if skip and not node.queue and not node.now_playing:
            await lavalink.stop(event.guild_id)

async def _join(ctx: lightbulb.Context) -> Optional[hikari.Snowflake]:
    assert ctx.guild_id is not None

    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]

    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None

    channel_id = voice_state[0].channel_id

    if HIKARI_VOICE:
        assert ctx.guild_id is not None

        await plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True, self_mute=True)
        connection_info = await plugin.d.lavalink.wait_for_full_connection_info_insert(ctx.guild_id)

    else:
        try:
            connection_info = await plugin.d.lavalink.join(ctx.guild_id, channel_id)
        except TimeoutError:
            await ctx.respond("It seems that there's an issue. I might not have the right permissions.")
            embed=hikari.Embed(title="**Timeout error**", description=f"A timeout error just occured.", color=0xC80000, timestamp=datetime.datetime.now().astimezone())
            await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
            return None

    await plugin.d.lavalink.create_session(connection_info)

    return channel_id

@plugin.listener(hikari.ShardReadyEvent)
async def start_lavalink(event: hikari.ShardReadyEvent) -> None:
    builder = (
        lavasnek_rs.LavalinkBuilder(event.my_user.id, TOKEN)
        .set_host(LAVALINK_SERVER).set_password(LAVALINK_PASSWORD).set_port(LAVALINK_PORT)
    )
    if HIKARI_VOICE:
        builder.set_start_gateway(False)
    lava_client = await builder.build(EventHandler())
    plugin.d.lavalink = lava_client

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("join", "Niko joins your voice channel", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def join(ctx: lightbulb.Context) -> None:
    channel_id = await _join(ctx)
    if channel_id:
        embed = hikari.Embed(title="**Joined voice channel.**", colour=0x6100FF)
        await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("leave", "Niko leaves your voice channel.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def leave(ctx: lightbulb.Context) -> None:
    await plugin.d.lavalink.destroy(ctx.guild_id)
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if HIKARI_VOICE:
        if ctx.guild_id is not None:
            await plugin.bot.update_voice_state(ctx.guild_id, None)
            await plugin.d.lavalink.wait_for_connection_info_remove(ctx.guild_id)
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    else:
        await plugin.d.lavalink.leave(ctx.guild_id)
    await plugin.d.lavalink.remove_guild_node(ctx.guild_id)
    await plugin.d.lavalink.remove_guild_from_loops(ctx.guild_id)
    embed = hikari.Embed(title="**Left voice channel.**", colour=0x6100FF)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("song", "The name of the song (or url) that you want to play.", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("play", "Niko plays your desired song.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:
    query = ctx.options.song
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    await _join(ctx)
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    firsttrack = node.get_data().get("First")
    chanid = node.get_data().get("ChannelID")
    ID = ctx.channel_id
    node.set_data({"ChannelID": ID, "First": False})
    if "youtube" in query:
        embed=hikari.Embed(title="**Supported Platforms : Soundcloud, Spotify, Bandcamp, Vimeo, Twitch and HTTP Streams.**", color=0xC80000)
        return await ctx.respond(embed=embed)
    if "youtu.be" in query:
        embed=hikari.Embed(title="**Supported Platforms : Soundcloud, Spotify, Bandcamp, Vimeo, Twitch and HTTP Streams.**", color=0xC80000)
        return await ctx.respond(embed=embed)
    if "https://open.spotify.com/playlist" in ctx.options.song:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
        playlist_link = f"{ctx.options.song}"
        playlist_URI = playlist_link.split("/")[-1].split("?")[0]
        track_uris = [x["track"]["uri"] for x in sp.playlist_tracks(playlist_URI)["items"]]
        for track in sp.playlist_tracks(playlist_URI)["items"]:
         track_name = track["track"]["name"]
         track_artist = track["track"]["artists"][0]["name"]
         queryfinal = f"{track_name} " + " " + f"{track_artist}" 
         result = f"ytmsearch:{queryfinal}"
         query_information = await plugin.d.lavalink.get_tracks(result)
         try:
          await plugin.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
         except:
          pass
        embed=hikari.Embed(title="**Added Playlist To The Queue.**", color=0x6100FF)
        await ctx.respond(embed=embed)
        embed=hikari.Embed(title="**Playlist Added**", description=f"Spotify playlist was just added to the queue.", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return
    if "https://open.spotify.com/album" in ctx.options.song:	
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
        album_link = f"{query}"
        album_id= album_link.split("/")[-1].split("?")[0]
        for track in sp.album_tracks(album_id)["items"]:
         track_name = track["name"]
         track_artist = track["artists"][0]["name"]
         queryfinal = f"{track_name} " + f"{track_artist}" 
         result = f"ytmsearch:{queryfinal}"
         query_information = await plugin.d.lavalink.get_tracks(result)
         try:
          await plugin.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
         except:
          pass
        embed=hikari.Embed(title="**Added Album To The Queue.**", color=0x6100FF)
        await ctx.respond(embed=embed)
        embed=hikari.Embed(title="**Album Added**", description=f"Spotify album was just added to the queue.", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return
    if "https://open.spotify.com/track" in ctx.options.song:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
        track_link = f"{query}"
        track_id= track_link.split("/")[-1].split("?")[0]
        track = f"spotify:track:{track_id}"
        spotifytrack = sp.track(track)
        trackname = spotifytrack['name'] + " " + spotifytrack["artists"][0]["name"]
        result = f"ytmsearch:{trackname}"
        query_information = await plugin.d.lavalink.get_tracks(result)   
        await plugin.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
        embed=hikari.Embed(title="Added Song To The Queue",color=0x6100FF) 
        await ctx.respond(embed=embed) 
        embed=hikari.Embed(title="**Song Added**", description=f"Spotify track was just added to the queue.", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return
    if not re.match(URL_REGEX, query):
      sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
      results = sp.search(q=f'{query}', limit=1)
      for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]
      try:
        queryfinal = f"{querytrack}" + " " + f"{queryartist}"
      except:
        embed = hikari.Embed(title="**Unable to find any songs! Please try to include the song's artists name as well.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        embed=hikari.Embed(title="**Unable To Find Any Tracks**", description=f"Unable to find tracks for **{query}**", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return
      result = f"ytmsearch:{queryfinal}"
      query_information = await plugin.d.lavalink.get_tracks(result)
    else:
        query_information = await plugin.d.lavalink.get_tracks(query)
    if not query_information.tracks:
        embed = hikari.Embed(title="**Unable to find any songs! Please try to include the song's artists name as well.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        embed=hikari.Embed(title="**Unable To Find Any Tracks**", description=f"Unable to find tracks for **{query}**", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return
    if not node or not node.now_playing:
     node.set_data({"ChannelID": ID, "First": True})
     sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
     results = sp.search(q=f'{query}', limit=1)
     for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
     embed1=hikari.Embed(title="**Now Playing**",color=0x6100FF)
     try:
        embed1.add_field(name="Name", value=f"{[querytrack]}({track['external_urls']['spotify']})", inline=False)
     except:
        embed1.add_field(name="Name", value=f"{query_information.tracks[0].info.title}", inline=False)
     try:
        embed1.add_field(name="Artist", value=f"{[queryartist]}({track['artists'][0]['external_urls']['spotify']})", inline=False)
     except:
        embed1.add_field(name="Artist", value=f"{query_information.tracks[0].info.author}", inline=False)
     try:
        embed1.add_field(name="Album", value=f"{[track['album']['name']]}({track['album']['external_urls']['spotify']})", inline=False)
     except:
        pass
     try:
        length = divmod(query_information.tracks[0].info.length, 60000)
        embed1.add_field(name="Duration", value=f"{int(length[0])}:{round(length[1]/1000):02}")
     except:
        pass
     try:
        embed1.add_field(name="Release Date", value=f"{track['album']['release_date']}", inline=False)
     except:
        pass
     try:
        embed1.set_thumbnail(f"{track['album']['images'][0]['url']}")
     except:
        pass
     await ctx.respond(embed=embed1)
    else:
     node.set_data({"ChannelID": ID, "First": False})
     sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
     results = sp.search(q=f'{query}', limit=1)
     for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
     embed=hikari.Embed(title="**Queued Track**",color=0x6100FF)
     try:
        embed.add_field(name="Name", value=f"{[querytrack]}({track['external_urls']['spotify']})", inline=False)
     except:
        embed.add_field(name="Name", value=f"{query_information.tracks[0].info.title}", inline=False)
     try:
        embed.add_field(name="Artist", value=f"{[queryartist]}({track['artists'][0]['external_urls']['spotify']})", inline=False)
     except:
        embed.add_field(name="Artist", value=f"{query_information.tracks[0].info.author}", inline=False)
     try:
        embed.add_field(name="Album", value=f"{[track['album']['name']]}({track['album']['external_urls']['spotify']})", inline=False)
     except:
        pass
     try:
        length = divmod(query_information.tracks[0].info.length, 60000)
        embed.add_field(name="Duration", value=f"{int(length[0])}:{round(length[1]/1000):02}")
     except:
        pass
     try:
        embed.add_field(name="Release Date", value=f"{track['album']['release_date']}", inline=False)
     except:
        pass
     try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
     except:
        pass
     await ctx.respond(embed=embed)
    try:
        await plugin.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
    except lavasnek_rs.NoSessionPresent:
        pass

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("song", "The name of the song that you want to search.", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("search", "Niko searches for your a song based on your query.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def search(ctx: lightbulb.Context) -> None:
    query = ctx.options.song
    if not re.match(URL_REGEX, query):
      sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
      results = sp.search(q=f'{query}', limit=10)
      embed = hikari.Embed(title=f"**Results for {query}**", colour=0x6100FF)
      embed.add_field(name="Top 10 Results", value=f"\n".join([f"**{i}.** {[track['name']]}({track['external_urls']['spotify']}) - {track['artists'][0]['name']}" for i, track in enumerate(results['tracks']['items'], start=1)]))
      results1 = sp.search(q=f'{query}', limit=1)
      for idx, track in enumerate(results1['tracks']['items']):
        querytrack = track['name']
      try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
      except:
        pass
      try:
        await ctx.respond(embed=embed)
      except:
        embed = hikari.Embed(title="**Unable to find any songs! Please try to include the song's artists name as well.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        embed=hikari.Embed(title="**Unable To Find Any Tracks**", description=f"Unable to find tracks for **{query}**", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
        await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
        return    
    else:
        embed=hikari.Embed(title="**URL'S are not supported!**", colour=0xC80000)
        await ctx.respond(embed=embed)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("stop", "Niko stops the currently playing song. (Type skip if you would like to move onto the next song.)", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed = hikari.Embed(title=f"**Stopped {node.now_playing.track.info.title}.**", description="Type **/skip** to play the next song.", colour=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await plugin.d.lavalink.stop(ctx.guild_id)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("percentage", "What to change the volume to.", int, required = True)
@lightbulb.command("volume", "Change the volume.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def volume(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    if ctx.options.percentage > 150:
        embed = hikari.Embed(title="**Volume cannot be greater than 150%.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    if ctx.options.percentage < 0:
        embed = hikari.Embed(title="**Volume must be greater than 0%.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    await plugin.d.lavalink.volume(ctx.guild_id, ctx.options.percentage)
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed=hikari.Embed(title=f"**Volume is now at {ctx.options.percentage}%**", color=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("time", "What time you would like to seek to. Example : 1:10", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("seek", "Seek to a specific point in a song.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def seek(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    if not (match := re.match(TIME_REGEX, ctx.options.time)):
            embed = hikari.Embed(title="**Invalid time entered.**", colour=0xC80000)
            await ctx.respond(embed=embed)
            return
    if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
    else:
            secs = int(match.group(1))
    await plugin.d.lavalink.seek_millis(ctx.guild_id, secs * 1000)
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed = hikari.Embed(title=f"**Seeked {node.now_playing.track.info.title}.**", colour=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)

        embed.add_field(name="Current Position", value=f"{ctx.options.time}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("replay", "Niko replays the current song.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def replay(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    await plugin.d.lavalink.seek_millis(ctx.guild_id, 0000)
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed = hikari.Embed(title=f"**Replaying {node.now_playing.track.info.title}.**", colour=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await ctx.respond(embed=embed)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("skip", "Niko skips to the next song (if any).", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def skip(ctx: lightbulb.Context) -> None:
    skip = await plugin.d.lavalink.skip(ctx.guild_id)
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    if not skip:
        embed = hikari.Embed(title="**There are no more tracks left in the queue.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    else:
        if not node.queue and not node.now_playing:
            await plugin.d.lavalink.stop(ctx.guild_id)
    recommend_enabled = node.get_data().get("recommend")
    loop_enabled = node.get_data().get("loop")
    if recommend_enabled:
        embed = hikari.Embed(title=f"**Skipped {skip.track.info.title} - {skip.track.info.author}.**", description=f"Recommendations have been enabled. Autoplaying the next track.", colour=0x6100FF)
        await ctx.respond(embed=embed)
    elif loop_enabled:
        embed = hikari.Embed(title=f"**Skipped {skip.track.info.title} - {skip.track.info.author}.**", description=f"Queueloop has been enabled. Playing the next track.", colour=0x6100FF)
        await ctx.respond(embed=embed)
    elif (len(node.queue) == 0):
        embed = hikari.Embed(title=f"**Skipped {skip.track.info.title} - {skip.track.info.author}.**", description=f"No songs left in the queue.", colour=0x6100FF)
        await ctx.respond(embed=embed)
    else:
        embed = hikari.Embed(title=f"**Skipped {skip.track.info.title} - {skip.track.info.author}.**", colour=0x6100FF)
        await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("pause", "Niko pauses the currently playing track.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    await plugin.d.lavalink.pause(ctx.guild_id)
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed = hikari.Embed(title=f"**Paused {node.now_playing.track.info.title}.**", description="Type **/resume** to resume the song.", colour=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("resume", "Niko resumes playing the currently playing track.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def resume(ctx: lightbulb.Context) -> None:
    await plugin.d.lavalink.resume(ctx.guild_id)
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed = hikari.Embed(title=f"**Resumed {node.now_playing.track.info.title}.**", description="Type **/pause** the pause the song.", colour=0x6100FF)
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("song", "The name of the song you want lyrics for.", modifier=lightbulb.OptionModifier.CONSUME_REST)
@lightbulb.command("lyrics", "Niko searches for the lyrics of any song of your choice!", auto_defer=True, ephemeral=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def lyrics(ctx: lightbulb.Context) -> None:
     genius = lyricsgenius.Genius(f"{GENIUS_API_KEY}")
     genius.verbose = True
     genius.remove_section_headers = False
     genius.skip_non_songs = True
     song = genius.search_song(f"{ctx.options.song}")
     try:
      test_stirng = f"{song.lyrics}"
     except:
      embed = hikari.Embed(title="**Unable to find any lyrics!**", colour=0xC80000)
      await ctx.respond(embed=embed)
      embed=hikari.Embed(title="**Unable To find Lyrics**", description=f"Unable to find lyrics for **{ctx.options.song}**", color=0x6100FF, timestamp=datetime.datetime.now().astimezone())
      await plugin.bot.rest.create_message(LOGGING_CHANNEL, embed=embed)
     total = 1
     for i in range(len(test_stirng)):
       if(test_stirng[i] == ' ' or test_stirng == '\n' or test_stirng == '\t'):
         total = total + 1
     if total > 650:
       embed=hikari.Embed(title="**Character Limit Exceeded!**", description=f"The lyrics in this song are too long. (Over 6000 characters)", color=0xC80000)
       await ctx.respond(embed=embed)
     sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
     results = sp.search(q=f'{ctx.options.song}', limit=1)
     for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]
        queryfinal =f"{queryartist}" + " " + f"{querytrack}"
     embed2=hikari.Embed(title=f"**{querytrack}**" ,description=f"{song.lyrics}", color=0x6100FF)
     await ctx.respond(embed=embed2)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("nowplaying", "See what's currently playing.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def now_playing(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f"{node.now_playing.track.info.author} {node.now_playing.track.info.title}", limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    embed=hikari.Embed(title="**Currently Playing**",color=0x6100FF)
    try:
        embed.add_field(name="Name", value=f"{[querytrack]}({track['external_urls']['spotify']})", inline=False)
    except:
        embed.add_field(name="Name", value=f"{node.now_playing.track.info.title}", inline=False)
    try:
        embed.add_field(name="Artist", value=f"{[queryartist]}({track['artists'][0]['external_urls']['spotify']})", inline=False)
    except:
        embed.add_field(name="Artist", value=f"{node.now_playing.track.info.author}", inline=False)
    try:
        embed.add_field(name="Album", value=f"{[track['album']['name']]}({track['album']['external_urls']['spotify']})", inline=False)
    except:
        pass
    try:
        length = divmod(node.now_playing.track.info.length, 60000)
        position = divmod(node.now_playing.track.info.position, 60000)
        embed.add_field(name="Duration Played", value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}")
    except:
        pass
    try:
        embed.add_field(name="Release Date", value=f"{track['album']['release_date']}", inline=False)
    except:
        pass
    try:
        embed.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("queue", "Niko shows you the queue.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def queue(ctx: lightbulb.Context) -> None:
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    if len(node.queue) == 1:
        embed = hikari.Embed(title="**The queue is currently empty.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    songs = [f'{tq.track.info.title} - {tq.track.info.author} ({int(divmod(tq.track.info.length, 60000)[0])}:{round(divmod(tq.track.info.length, 60000)[1]/1000):02})' for i, tq in enumerate(node.queue[1:], start=1)]
    chunks = [songs[i : i + 10] for i in range(0, len(songs), 10)]
    embeds = []
    i = 1
    for chunk in chunks:
        texts = []
        for track in chunk:
            texts.append(f"**{i}.** {track}")
            i += 1
        names = "\n".join(texts)
        songs = hikari.Embed(title="**The Queue**", description=names, color=0x6100FF)
        embeds.append(songs)
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    results = sp.search(q=f'{node.queue[1].track.info.author} {node.queue[1].track.info.title}', limit=1)
    for idx, track in enumerate(results['tracks']['items']):
        querytrack = track['name']
        queryartist = track["artists"][0]["name"]	
    try:
        songs.set_thumbnail(f"{track['album']['images'][0]['url']}")
    except:
        pass
    navigator = nav.NavigatorView(pages=embeds)
    await navigator.send(ctx.interaction)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("index", "Index for the song you want to remove.", int, required = True)
@lightbulb.command("remove", "Niko removes a song from the queue.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def remove(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    index = int(ctx.options.index)
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if index == 0:
        embed = hikari.Embed(title=f"**You cannot remove a song that is currently playing.**",color=0xC80000)
        return await ctx.respond(embed=embed)
    try:
     queue = node.queue
     song_to_be_removed = queue[index]
    except:
        embed = hikari.Embed(title=f"**Incorrect position entered.**",color=0xC80000)
        return await ctx.respond(embed=embed)
    try:
        queue.pop(index)
    except:
        pass
    node.queue = queue
    await plugin.d.lavalink.set_guild_node(ctx.guild_id, node)
    embed = hikari.Embed(title=f"**Removed {song_to_be_removed.track.info.title}.**",color=0x6100FF,)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("position", "The song's position in the queue.", int, required = True)
@lightbulb.command("skipto", "Niko goes to a different song in the queue.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def skipto(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    index = int(ctx.options.position)
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if index == 0:
        embed = hikari.Embed(title=f"**You cannot move to a song that is currently playing.**",color=0xC80000)
        return await ctx.respond(embed=embed)
    if index == 1:
        embed = hikari.Embed(title=f"**Skipping to the next song.**",color=0xC80000)
        await plugin.d.lavalink.skip(ctx.guild_id)
        return await ctx.respond(embed=embed)
    try:
     queue = node.queue
     song_to_be_skipped = queue[index]
    except:
        embed = hikari.Embed(title=f"**Incorrect position entered.**",color=0xC80000)
        return await ctx.respond(embed=embed)
    queue.insert(1, queue[index])
    queue.pop(index)
    queue.pop(index)
    node.queue = queue
    await plugin.d.lavalink.set_guild_node(ctx.guild_id, node)
    await plugin.d.lavalink.skip(ctx.guild_id)
    embed = hikari.Embed(title=f"**Skipped to {song_to_be_skipped.track.info.title}.**",color=0x6100FF)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("current_position", "The song's current position in the queue.", int, required = True)
@lightbulb.option("new_position", "The song's new position in the queue.", int, required = True)
@lightbulb.command("move", "Move a song to a different position in the queue.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def move(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    new_index = int(ctx.options.new_position)
    old_index = int(ctx.options.current_position)
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not len(node.queue) >= 1:
        embed = hikari.Embed(title=f"**There is only 1 song in the queue.**",color=0xC80000)
        await ctx.respond(embed=embed)
        return
    queue = node.queue
    song_to_be_moved = queue[old_index]
    try:
        queue.pop(old_index)
        queue.insert(new_index, song_to_be_moved)
    except:
        embed = hikari.Embed(title=f"**Incorrect position entered.**",color=0xC80000)
        await ctx.respond(embed=embed)
        return
    node.queue = queue
    await plugin.d.lavalink.set_guild_node(ctx.guild_id, node)
    embed = hikari.Embed(title=f"**Moved {song_to_be_moved.track.info.title} to position {new_index}.**", color=0x6100FF)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("empty", "Niko empties the queue.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def empty(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    await plugin.d.lavalink.stop(ctx.guild_id)
    await plugin.d.lavalink.leave(ctx.guild_id)
    await plugin.d.lavalink.remove_guild_node(ctx.guild_id)
    await plugin.d.lavalink.remove_guild_from_loops(ctx.guild_id)
    await plugin.bot.update_voice_state(ctx.guild_id, None)
    await plugin.d.lavalink.wait_for_connection_info_remove(ctx.guild_id)
    await _join(ctx)
    embed=hikari.Embed(title="**Emptied the queue.**",color=0x6100FF)
    await ctx.respond(embed=embed)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("newreleases", "See the latest releases for the day.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def newreleases(ctx: lightbulb.Context) -> None:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    response = sp.new_releases(limit=21)
    albums = response['albums']
    today = date.today()
    embed=hikari.Embed(title=f"**New Releases - {today}**", color=0x6100FF)
    embed.add_field(name="Latest Tracks", value=f"\n".join([f"**{i}.** {item['name']}" for i, item in enumerate(albums['items'][1:], start=1)]))
    img = response['albums']['items'][1]['images'][0]['url']
    try:
      embed.set_thumbnail(img)
    except:
        pass
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("trending", "See the latest trending tracks.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def trending(ctx: lightbulb.Context) -> None:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTCLIENT_ID,client_secret=SPOTCLIENT_SECRET))
    playlist_URI = "37i9dQZF1DXcBWIGoYBM5M"
    track_uris = [x["track"]["uri"] for x in sp.playlist_tracks(playlist_URI)["items"]]
    track = sp.track(track_uris[1])
    today = date.today()
    embed=hikari.Embed(title=f"**Trending Tracks - {today}**", color=0x6100FF)
    embed.add_field(name="Top 20 Tracks Of The Day", value=f"\n".join([f"**{i}.** {track['track']['name']}" for i, track in enumerate(sp.playlist_tracks(playlist_URI, limit=21)["items"][1:], start=1)]))
    img = track['album']['images'][0]['url']
    try:
      embed.set_thumbnail(img)
    except:
        pass
    await ctx.respond(embed=embed)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("recommend", "Niko adds recommended tracks based on what's playing.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def recommend(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    recommend_enabled = node.get_data().get("recommend")
    if recommend_enabled:
        ID = ctx.channel_id
        node.set_data({"ChannelID": ID, "First": True, "recommend": False})
        embed = hikari.Embed(title="**Disabled recommendations.**", description="Recommended tracks will no longer be queued.", color=0x6100FF)
        await ctx.respond(embed=embed)
    else:
        ID = ctx.channel_id
        node.set_data({"ChannelID": ID, "First": False, "recommend": True})
        embed = hikari.Embed(title="**Enabled recommendations.**", description=f"Recommended tracks will be queued after **{node.now_playing.track.info.title}** finishes.", color=0x6100FF)
        await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("queueloop", "Niko loops the entire queue!", auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def queueloop(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    loop_enabled = node.get_data().get("loop")
    if loop_enabled:
        ID = ctx.channel_id
        node.set_data({"ChannelID": ID, "First": True,"loop": False})
        embed = hikari.Embed(title="**Disabled the queue loop.**", description="No longer looping tracks in the queue.", color=0x6100FF)
        await ctx.respond(embed=embed)
    else:
        ID = ctx.channel_id
        node.set_data({"ChannelID": ID, "First": False,"loop": True})
        embed = hikari.Embed(title="**Enabled the queue loop.**", description=f"Looping all **{len(node.queue)}** tracks in the queue.", color=0x6100FF)
        await ctx.respond(embed=embed)
    
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("invite", "Invite Niko to other servers!", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def invite(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title="**A Few Related Links.**",color=0x6100FF)
    view = miru.View()
    view.add_item(miru.Button(url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands", label="Invite me!"))
    await ctx.respond(embed=embed, components=view.build())
        
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("vote", "Vote for Niko!", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def vote(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title="**Click the button below to vote for me.**",color=0x6100FF)
    view = miru.View()
    view.add_item(miru.Button(url="https://top.gg/bot/915595163286532167/vote", label="Vote for me!"))
    await ctx.respond(embed=embed, components=view.build())
        
@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("support", "Visit my support server!", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def vote(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title="**Click the button below to join my support server.**",color=0x6100FF)
    view = miru.View()
    view.add_item(miru.Button(url="https://discord.gg/grSvEPYtDF", label="Support Server!"))
    await ctx.respond(embed=embed, components=view.build())

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("donate", "Help developing Niko by donating!", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def donate(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title="**Let’s all come together and help fund Niko Music to keep it alive and perform EVEN better! Click the button below to donate! **",color=0x6100FF)
    view = miru.View()
    view.add_item(miru.Button(url="https://www.paypal.com/paypalme/NMdonations", label="Donate!"))
    await ctx.respond(embed=embed, components=view.build())

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("shuffle", "Niko shuffles the queue.", auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def shuffle(ctx: lightbulb.Context) -> None:
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not voice_state:
        embed = hikari.Embed(title="**You are not in a voice channel.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return None
    node = await plugin.d.lavalink.get_guild_node(ctx.guild_id)
    if not node or not node.now_playing:
        embed = hikari.Embed(title="**There are no songs playing at the moment.**", colour=0xC80000)
        await ctx.respond(embed=embed)
        return
    if not len(node.queue) > 1:
        embed = hikari.Embed(title="**There is only 1 song in the queue.**", color=0xC80000)
        return await ctx.respond(embed=embed)

    queue = node.queue[1:] # Because Index 0 is currently playing song and we don't wanna shuffle that!
    random.shuffle(queue) # Randomly shuffling the queue!
    queue.insert(0, node.queue[0]) # Inserting the now playing song back into the queue
    node.queue = queue
    await plugin.d.lavalink.set_guild_node(ctx.guild_id, node)
    embed = hikari.Embed(title="**Shuffled the Queue.**", color=0x6100FF)
    await ctx.respond(embed=embed)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("help", "See a list of all my commands!", auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def help(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title="**Help Center**",color=0x6100FF)
    embed.add_field(name="/join", value="Niko joins your VC.", inline=True)
    embed.add_field(name="/leave", value="Niko leaves your VC.", inline=True)
    embed.add_field(name="/play", value="Niko plays your song of choice.", inline=True)
    embed.add_field(name="/nowplaying", value="See what's currently playing.", inline=True)
    embed.add_field(name="/queue", value="See the queue.", inline=True)
    embed.add_field(name="/pause", value="Niko pauses the song.", inline=True)
    embed.add_field(name="/resume", value="Niko resumes the song.", inline=True)
    embed.add_field(name="/skip", value="Niko skips to the next song in the queue.", inline=True)
    embed.add_field(name="/replay", value="Niko replays the song.", inline=True)
    embed.add_field(name="/recommend", value="Niko adds related tracks to the queue.", inline=True)
    embed.add_field(name="/stop", value="Niko stops the song.", inline=True)
    embed.add_field(name="/volume", value="Adjust the volume.", inline=True)
    embed.add_field(name="/seek", value="Seek to a specific part time in a track.", inline=True)
    embed.add_field(name="/lyrics", value="Niko shows you the lyrics for most songs.", inline=True)
    embed.add_field(name="/empty", value="Niko empties the queue.", inline=True)
    embed.add_field(name="/shuffle", value="Niko shuffles the queue.", inline=True)
    embed.add_field(name="/skipto", value="Niko moves to a different song in the queue.", inline=True)
    embed.add_field(name="/move", value="Move tracks to different positions in the queue.", inline=True)
    embed.add_field(name="/search", value="Move searches for a track based on your query.", inline=True)
    embed.add_field(name="/queueloop", value="Niko loops the entire queue.", inline=True)
    embed.add_field(name="/ping", value="See Niko's ping.", inline=True)
    embed.add_field(name="/newreleases", value="See the latest releases for the day.", inline=True)
    embed.add_field(name="/trending", value="See the latest trending tracks for the day.", inline=True)
    embed.add_field(name="/invite", value="Invite niko to other servers.", inline=True)
    view = miru.View()
    view.add_item(miru.Button(url="https://www.paypal.com/paypalme/NMdonations", label="Donate!"))
    view.add_item(miru.Button(url="https://github.com/ZingyTomato/Niko-Music", label="Visit my project!"))
    view.add_item(miru.Button(url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands", label="Invite me!"))
    view.add_item(miru.Button(url="https://top.gg/bot/915595163286532167/vote", label="Vote for me!"))
    view.add_item(miru.Button(url="https://discord.gg/grSvEPYtDF", label="Support Server!"))
    await ctx.respond(embed=embed, components=view.build())

if HIKARI_VOICE:

    @plugin.listener(hikari.VoiceStateUpdateEvent)
    async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
        plugin.d.lavalink.raw_handle_event_voice_state_update(
            event.state.guild_id,
            event.state.user_id,
            event.state.session_id,
            event.state.channel_id,
        )

    @plugin.listener(hikari.VoiceServerUpdateEvent)
    async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
        await plugin.d.lavalink.raw_handle_event_voice_server_update(event.guild_id, event.endpoint, event.token)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(plugin)
