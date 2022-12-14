import discord
from discord import app_commands
from discord.ext import tasks
import wavelink, asyncio, re
from music import Music
from credentials import *

### Defenitions
intents = discord.Intents.default() ## Default intents are enough as slash commands are used.
client = discord.Client(intents=intents)
slash = app_commands.CommandTree(client) ## Slash commands.
music = Music()

### Bot Events
@client.event
async def on_ready(): ## Fires when the bot is ready.
    await slash.sync() ## Sync slash comands.
    await asyncio.sleep(10) ## Give enough time for the lavalink server to boot up before connecting.
    client.loop.create_task(connect_nodes()) ## Create task to connect to the lavalink server.
    print("Niko is Ready!")
    await update_status.start() ## Start the update status loop.

@tasks.loop(minutes=5)
async def update_status(): ## Updates the bot's status every 5 minutes.
    server_count = client.guilds ## Retrieve all the bots servers.
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, 
    name=f'to /play in {len(server_count)} servers!')) ## Update the status with bot's the guild count.

### Lavalink Events
@client.event
async def on_wavelink_node_ready(node: wavelink.Node): ## Fires when the lavalink server is connected
    print(f'Node: <{node.identifier}> is ready!') 

@client.event
async def on_wavelink_track_end(player: wavelink.Player, track, reason): ## Fires when a track ends.
    ctx = player.reply ## Retrieve the guild's channel id.
    
    if all(member.bot for member in player.channel.members): ## If there are no members in the vc, leave.
        player.queue.clear() ## Clear the queue.
        await player.stop() ## Stop the currently playing track.
        await player.disconnect() ## Leave the VC.
        await ctx.send(embed=await music.left_due_to_inactivity())
    
    elif not player.queue.is_empty and not player.loop and not player.queue_loop: ## If the queue is not empty and the loop is disabled, play the next track.
        next_track = await player.queue.get_wait()  ## Retrieve the queue.
        await player.play(next_track)

    elif player.loop: ## If the loop is enabled, replay the track using the existing `looped_track` variable.
        await player.play(player.looped_track)

    elif player.queue_loop: ## If the queue loop is enabled, replay the track using the existing `looped_track` var.
        player.queue.put(player.queue_looped_track) ## Add the current track back to the queue. 
        next_track = await player.queue.get_wait()  ## Retrieve the queue.
        await player.play(next_track)
    
    else: ## Otherwise, stop the track.
        await player.stop() 
        await ctx.send(embed=await music.no_tracks_in_queue(), delete_after=15) ## Let the user know that there are no more tracks in the queue.

    logging_channel = client.get_channel(int(LOGGING_CHANNEL_ID)) ## Retrieve the logging channel.
    await logging_channel.send(embed=await music.log_track_finished(track, player.guild)) ## Send the log embed.

@client.event
async def on_wavelink_track_start(player: wavelink.Player, track): ## Fires when a track starts.
    ctx = player.reply ## Retrieve the guild's channel id.
    
    if player.queue_loop: ## If the queue loop is enabled, assign queue_looped_track to the current track.
        player.queue_looped_track = track
    
    embed = await music.display_track(track, player.guild, False, False) ## Build the track info embed.
    await ctx.send(embed=embed, delete_after=60) ## Send the embed when a track starts and delete it after 60 seconds.
    
    logging_channel = client.get_channel(int(LOGGING_CHANNEL_ID)) ## Retrieve the logging channel.
    await logging_channel.send(embed=await music.log_track_started(track, player.guild)) ## Send the log embed.

@client.event
async def on_voice_state_update(member: discord.member.Member, before: discord.member.VoiceState,
after: discord.member.VoiceState): ## Fires when the bot is disconnected/connected to a VC.

    if member.id == client.user.id: ## Check whether or not the voice update was caused by the bot.
        player: wavelink.Player = await music.get_player(member.guild) ## Retrieve the player.

        if before.channel and after.channel is None: ## If the bot was previsously in a VC, disconnect to avoid errors when rejoining the VC.
            try:
                await player.disconnect()
            except AttributeError: ## Occurs when /leave is entered as the bot has no player once disconnected.
                pass

        else: ## Otherwise, pass.
            pass

async def connect_nodes():
    await client.wait_until_ready() ## Wait until the bot is ready.
    await wavelink.NodePool.create_node(bot=client, host=LAVALINK_HOST,
        port=LAVALINK_PORT,
        password=LAVALINK_PASS) ## Connect to the lavalink server.

### Bot Commands
@slash.command(name="join", description="Niko joins your voice channel.")
async def join(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif not interaction.guild.voice_client: ## If user is in a VC and bot is not, join it.
        await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        return await interaction.followup.send(embed=await music.in_vc())
    
    else: ## If bot is already in a VC, respond.
        return await interaction.followup.send(embed=await music.already_in_vc())

@slash.command(name="leave", description="Niko leaves your voice channel.")
async def leave(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if interaction.guild.voice_client and interaction.guild.voice_client.channel == interaction.user.voice.channel: ## If bot and the user are in the same VC, leave it.        
        await interaction.guild.voice_client.disconnect() 
        return await interaction.followup.send(embed=await music.left_vc()) 
    
    elif not interaction.guild.voice_client: ## If bot is not in VC, respond.
        return await interaction.followup.send(embed=await music.already_left_vc())

    else: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
        
@slash.command(name="pause", description="Niko pauses the currently playing track.")
async def pause(interaction: discord.Interaction):
    await interaction.response.defer()

    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client and interaction.guild.voice_client.channel == interaction.user.voice.channel: ## If bot is in a VC, pause the currently playing track.
        player = await music.get_player(interaction.guild) ## Retrieve the current player.
        track = await music.get_track(interaction.guild) ## Retrieve currently playing track's info.
     
        if not player.is_paused(): ## If the current track is not paused, pause it.
            await interaction.guild.voice_client.pause()
            return await interaction.followup.send(embed=await music.common_track_actions(
                track, "Paused"))

        else: ## Otherwise, respond.
            return await interaction.followup.send(embed=await music.already_paused(track))
    
@slash.command(name="resume", description="Niko resumes the currently playing track.")
async def resume(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, resume the currently playing track.
        player = await music.get_player(interaction.guild) ## Retrieve the current player.
        track = await music.get_track(interaction.guild) ## Retrieve currently playing track's info.

        if player.is_paused(): ## If the current track is paused, resume it.
            await interaction.guild.voice_client.resume()
            return await interaction.followup.send(embed=await music.common_track_actions(
                track, "Resumed"))

        else: ## Otherwise, respond.
            return await interaction.followup.send(embed=await music.already_resumed(track))

@slash.command(name="stop", description="Niko stops the currently playing track.")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, stop the currently playing track.
        track = await music.get_track(interaction.guild) ## Retrieve currently playing track's info.
        player = await music.get_player(interaction.guild) ## Retrieve the current player.
        await interaction.followup.send(embed=await music.common_track_actions(
            track, "Stopped"))
        
        return await interaction.guild.voice_client.stop() ## Stop the track after sending the embed.

@slash.command(name="skip", description="Niko skips the currently playing track.")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, skip the currently playing track.
        track = await music.get_track(interaction.guild) ## Retrieve currently playing track's info.
        await interaction.followup.send(embed=await music.common_track_actions(
            track, "Skipped"))
        
        return await interaction.guild.voice_client.stop() ## Skip the track after sending the embed.

@slash.command(name="queue", description="Niko shows you the queue.")
async def queue(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, show the current queue.
        return await interaction.followup.send(embed=await music.show_queue(
            await music.get_queue(interaction.guild), interaction.guild)) ## Show the queue.

@slash.command(name="shuffle", description="Niko shuffles the queue.")
async def shuffle(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, shuffle the current queue.
        queue = await music.get_queue(interaction.guild) ## Retrieve the current queue.
        track = await music.get_track(interaction.guild) ## Retrieve the current track.
        player = await music.get_player(interaction.guild) ## Retrieve the current player.
    
        if len(queue) == 0: ## If there are no tracks in the queue, respond.
            return await interaction.followup.send(embed=await music.empty_queue())
        
        else:
            await music.shuffle(queue) ## Shuffle the queue.
            if not player.queue_loop: ## If the queue loop is not enabled, place the current track at the end of the queue.
                player.queue.put(track) ## Add the current track to the end of the queue.
            return await interaction.followup.send(embed=await music.shuffled_queue())

@slash.command(name="nowplaying", description="Niko shows you the currently playing song.")
async def nowplaying(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, resume the currently playing track.
        track = await music.get_track(interaction.guild) ## Retrieve currently playing track's info.
        player = await music.get_player(interaction.guild) ## Retrieve the current player.
        
        return await interaction.followup.send(embed=await music.display_track(
            track, interaction.guild, False, True))

@slash.command(name="volume", description="Niko adjusts the volume.")
@app_commands.describe(volume_percentage="The percentage to set the volume to. Accepted range: 0 to 100.")
async def volume(interaction: discord.Interaction, *, volume_percentage: int):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, resume the currently playing track.
        
        if volume_percentage > 100: ## Volume cannot be greater than 100%.
            return await interaction.followup.send(embed=await music.volume_too_high())
        
        else:
            await music.modify_volume(interaction.guild, volume_percentage) ## Adjust the volume to the specified percentage.
            return await interaction.followup.send(embed=await music.volume_set(volume_percentage))

@slash.command(name="remove", description="Niko removes a track from the queue.")
@app_commands.describe(track_index="The number of track to remove. Find out the track number using /queue.")
async def remove(interaction: discord.Interaction, *, track_index: int):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, try to remove the requested track.
        remove_msg = await music.queue_track_actions(await music.get_queue(interaction.guild), track_index, 
        "Removed") ## Store the info beforehand as the track will be removed.
        
        if remove_msg != False: ## If the track exists in the queue, respond.
            await music.remove_track(await music.get_queue(interaction.guild), track_index) ## Remove the track.
            return await interaction.followup.send(embed=remove_msg)
        
        else: ## If the track was not removed, respond.
            return await interaction.followup.send(embed=await music.track_not_in_queue())

@slash.command(name="skipto", description="Niko skips to a specific track in the queue.")
@app_commands.describe(track_index="The number of track to skip to. Find out the track number using /queue.")
async def skipto(interaction: discord.Interaction, *, track_index: int):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, try to remove the requested track.
        skipped_msg = await music.queue_track_actions(await music.get_queue(interaction.guild), track_index, 
        "Skipped to") ## Store the info beforehand as the track will be removed.
        
        if skipped_msg != False: ## If the track exists in the queue, respond.
            await music.skipto_track(interaction.guild, track_index) ## Skip to the requested track.
            await interaction.guild.voice_client.stop() ## Stop the currently playing track.
            return await interaction.followup.send(embed=skipped_msg)
        
        else: ## If the track was not skipped, respond.
            return await interaction.followup.send(embed=await music.track_not_in_queue())

@slash.command(name="empty", description="Niko empties the queue.")
async def empty(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, empty the queue.
        queue = await music.get_queue(interaction.guild) ## Retrieve the current queue.
        player = await music.get_player(interaction.guild) ## Retrieve the player.
    
        if len(queue) == 0: ## If there are no tracks in the queue, respond.
            return await interaction.followup.send(embed=await music.empty_queue())
        
        else: ## Otherwise, clear the queue.
            player.queue.clear()
            return await interaction.followup.send(embed=await music.cleared_queue()) 
        
@slash.command(name="loop", description="Niko loops the currently playing track.")
async def loop(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, enable/disable the loop.
        player = await music.get_player(interaction.guild) ## Retrieve the player.
        track = await music.get_track(interaction.guild) ## Retrieve the currently playing track.
        
        if not player.loop: ## If the loop is not enabled, enable it.
            await interaction.followup.send(embed=await music.common_track_actions(
            track, "Looping")) ## Send the msg before enabling the loop to avoid confusing embed titles.
            
            player.loop = True
            player.looped_track = track ## Store the currently playing track so that it can be looped.
            return 
        
        else: ## If the loop is already enabled, disable it.
            player.loop = False
            return await interaction.followup.send(embed=await music.common_track_actions(
            track, "Stopped looping"))

@slash.command(name="queueloop", description="Niko loops the current queue.")
async def queueloop(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    elif not await music.get_player(interaction.guild) or not await music.get_track(interaction.guild): ## If nothing is playing, respond.
        return await interaction.followup.send(embed=await music.nothing_is_playing())

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif interaction.guild.voice_client: ## If bot is in a VC, enable/disable the queue loop.
        player = await music.get_player(interaction.guild) ## Retrieve the player.
        track = await music.get_track(interaction.guild) ## Retrieve the currently playing track.
        queue = await music.get_queue(interaction.guild) ## Retrieve the current queue.
        
        if len(queue) < 1 and not player.queue_loop: ## If there is less than 1 track in the queue and there is not a current queueloop, respond.
            return await interaction.followup.send(embed=await music.less_than_1_track())

        if not player.queue_loop: ## If the queue loop is not enabled, enable it.
            await interaction.followup.send(embed=await music.common_track_actions(
            None, "Looping the queue")) ## Send the msg before enabling the queue loop to avoid confusing embed titles.
        
            player.queue_loop = True 
            player.queue_looped_track = track ## Add the currently playing track.
            return
        
        else: ## If the queue loop is already enabled, disable it.
            player.queue_loop = False
            player.queue_looped_track = None ## Prevents the current track from constantly being assigned.
            
            return await interaction.followup.send(embed=await music.common_track_actions(
            None, "Stopped looping the queue"))

@slash.command(name="newreleases", description="Niko shows you the newly released tracks of the day.")
async def newreleases(interaction: discord.Interaction):
    await interaction.response.defer()

    return await interaction.followup.send(embed=
     await music.display_new_releases(await music.get_new_releases())) ## Display the trending embed.

@slash.command(name="trending", description="Niko shows you the trending tracks of the day.")
async def trending(interaction: discord.Interaction):
    await interaction.response.defer()

    return await interaction.followup.send(embed=
     await music.display_trending(await music.get_trending())) ## Display the new releases embed.

@slash.command(name="vote", description="Vote for Niko to help grow the bot!")
async def vote(interaction: discord.Interaction):
    await interaction.response.defer()

    embed, view = await music.display_vote()

    return await interaction.followup.send(embed=embed, view=view) ## Display the vote embed.

@slash.command(name="support", description="Join my support server!")
async def support(interaction: discord.Interaction):
    await interaction.response.defer()

    embed, view = await music.display_support()

    return await interaction.followup.send(embed=embed, view=view) ## Display the vote embed.

@slash.command(name="invite", description="Invite Niko to other servers!")
async def invite(interaction: discord.Interaction):
    await interaction.response.defer()

    embed, view = await music.display_invite()

    return await interaction.followup.send(embed=embed, view=view) ## Display the invite embed.

@slash.command(name="search", description="Niko searches Spotify for tracks!")
@app_commands.describe(search_query="The name of the song to search for.")
async def search(interaction: discord.Interaction, *, search_query: str):
    await interaction.response.defer()

    return await interaction.followup.send(embed=await music.display_search(search_query)) ## Display the invite embed.

@slash.command(name="lyrics", description="Niko finds lyrics for (almost) any song!")
@app_commands.describe(song_name="The name of the song to retrieve lyrics for.")
async def lyrics(interaction: discord.Interaction, *, song_name: str):
    await interaction.response.defer(ephemeral=True) ## Send as an ephemeral to avoid clutter.

    lyrics_embed = await music.display_lyrics(await music.get_lyrics(song_name)) ## Retrieve the lyrics and embed it.

    try:
        return await interaction.followup.send(embed=lyrics_embed) ## Display the lyrics embed.
    except discord.HTTPException: ## If the lyrics are more than 4096 characters, respond.
        return await interaction.followup.send(embed=await music.lyrics_too_long())

@slash.command(name="play", description="Niko plays your desired song.")
@app_commands.describe(song_name="The name of the song to search for. Don't forget to include the artist's name as well!")
async def play(interaction: discord.Interaction , *, song_name: str):
    await interaction.response.defer()

    if not interaction.user.voice: ## If user is not in the bot's VC, respond.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif not interaction.guild.voice_client: ## If user is in a VC, join it.
        vc: wavelink.Player = await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())
    
    elif re.match(music.url_regex, song_name): ## If a URL is entered, respond.
        return await interaction.followup.send(embed=await music.urls_not_supported())
    
    else:
        vc: wavelink.Player = interaction.guild.voice_client ## Otherwise, initalize voice_client.
    
    try:
        track = await wavelink.YouTubeMusicTrack.search(song_name, return_first=True) ## Search for a song.
    except (IndexError, TypeError): ## If no results are found or an invalid query was entered, respond.
        return await interaction.followup.send(embed=await music.no_track_results())
    
    vc.reply = interaction.channel ## Store the channel id to be used in track_start.
    
    if vc.is_playing(): ## If a track is playing, add it to the queue.
        final_track = await music.gather_track_info(track.title, track.author, track) ## Modify the track info.
        await interaction.followup.send(embed=await music.added_track(final_track)) ## Use the modified track.
        return await vc.queue.put_wait(final_track) ## Add the modified track to the queue.
    
    else: ## Otherwise, begin playing.
        final_track = await music.gather_track_info(track.title, track.author, track) ## Modify the track info.
        msg = await interaction.followup.send(embed=await music.started_playing()) ## Send an ephemeral as now playing is handled by on_track_start.
        
        vc.loop = False ## Set the loop value to false as we have just started playing.
        vc.queue_loop = False ## Set the queue_loop value to false as we have just started playing.
        vc.looped_track = None ## Used to store the currently playing track in case the user decides to loop.
        vc.queue_looped_track = None ## Used to re-add the track in a queue loop.
        
        await vc.play(final_track) ## Play the modified track.
        await asyncio.sleep(5) 
        return await interaction.followup.delete_message(msg.id) ## Delete the message after 5 seconds.

@slash.command(name="url", description="Niko plays an album, playlist or track from a Spotify URL.")
@app_commands.describe(spotify_url="Any Spotify album, track or playlist URL.")
async def url(interaction: discord.Interaction, *, spotify_url: str):
    await interaction.response.defer()

    if not interaction.guild.voice_client: ## If bot is not in a VC, respond.
        await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)

    elif interaction.user.voice.channel != interaction.guild.voice_client.channel: ## If the user is not in the same VC as the bot.
        return await interaction.followup.send(embed=await music.user_not_in_vc())

    else: ## If bot is already in a VC, pass.
        pass

    if "https://open.spotify.com/playlist" in spotify_url: ## If a spotify playlist url is entered.
        playlist = await music.add_spotify_url(interaction.guild, spotify_url, interaction.channel, "playlist") ## Add the playlist to the queue.
            
        if playlist != None: ## If the playlist was added to the queue, respond.
            return await interaction.followup.send(embed=await music.display_playlist(spotify_url)) ## Display playlist info.
        else: 
            return await interaction.followup.send(embed=await music.invalid_url())

    elif "https://open.spotify.com/album" in spotify_url: ## If a spotify album url is entered.
        album = await music.add_spotify_url(interaction.guild, spotify_url, interaction.channel, "album") ## Add the album to the queue.
            
        if album != None: ## If the album was added to the queue, respond.
            return await interaction.followup.send(embed=await music.display_album(spotify_url)) ## Display album info.
        else:
            return await interaction.followup.send(embed=await music.invalid_url())

    elif "https://open.spotify.com/track" in spotify_url: ## If a spotify track url is entered.
        track = await music.add_track(interaction.guild, spotify_url, interaction.channel) ## Add the track to the queue, return tracks info.
            
        if track != None: ## If the track was added to the queue, respond.
            return await interaction.followup.send(embed=await music.added_track(track))
        else:
            return await interaction.followup.send(embed=await music.invalid_url())

    elif "https://open.spotify.com/show" in spotify_url or "https://open.spotify.com/artist" in spotify_url: ## Spotify podcasts or artists are not supported.
        return await interaction.followup.send(embed=await music.podcasts_not_supported())

    else: ## Let the user know that only spotify urls work.
        return await interaction.followup.send(embed=await music.only_spotify_urls()) 

if __name__ == "__main__":
    client.run(BOT_TOKEN) ## Run the bot.