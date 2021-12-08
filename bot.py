from math import floor
from discord.ext import commands
import discordSuperUtils
from discordSuperUtils import MusicManager
import discord
from discord_components import DiscordComponents, ComponentsBot, Button, Select, SelectOption

client_id = "CLIENTID"
client_secret = "CLIENTSECRET"

bot = commands.Bot(command_prefix="niko ", intents=discord.Intents.all(), help_command=None)
DiscordComponents(bot)
#MusicManager = MusicManager(bot, spotify_support=True)


MusicManager = MusicManager(
    bot, client_id=client_id, client_secret=client_secret, spotify_support=True
)

# if using spotify support use this instead ^^^

@MusicManager.event()
async def on_music_error(ctx, error):
    embed = discord.Embed(description=f"❌️ {error}")
    await ctx.reply(embed=embed, mention_author=False)
    raise error  # add your error handling here! Errors are listed in the documentation.

@MusicManager.event()
async def on_queue_end(ctx):
    embed = discord.Embed(description=f"❌️ The queue is **over**! Maybe get another song?")
    await ctx.reply(embed=embed, mention_author=False)
    # You could wait and check activity, etc...

@MusicManager.event()
async def on_inactivity_disconnect(ctx):
    embed = discord.Embed(description=f"❌️ Seems that this VC is **inactive**... I'mma head out.")
    await ctx.reply(embed=embed, mention_author=False)

@MusicManager.event()
async def on_play(ctx, player):
    embed = discord.Embed(description=f":notes: Now playing **{player}**")
    channel = ctx.author.voice.channel.id
    embed.add_field(name = ":point_down: Click Here To Listen Along!", value =f"<#{channel}>", inline = False)
    await ctx.reply(embed=embed, mention_author=False)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"niko help in {len(bot.guilds)} servers!"))
    for guild in bot.guilds:
      print(guild.name)
    print("Niko Muisc is ready.", bot.user)

@bot.command()
async def leave(ctx):
    if await MusicManager.leave(ctx):
        embed = discord.Embed(description=f"🔓️ I have **left** your VC! Bye I guess :(")
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def np(ctx):
    if player := await MusicManager.now_playing(ctx):
     duration_played = await MusicManager.get_player_played_duration(ctx, player)
     embed = discord.Embed(description=f":notes: Currently playing **{player}**")
     embed.add_field(name = ":alarm_clock: Duration Played", value = f"**{duration_played}**/**{player.duration}** seconds!", inline = False)
     await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def join(ctx):
    if await MusicManager.join(ctx):
         embed = discord.Embed(description=f"🔒️ I have **joined** your VC! Whats up?")
         await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def play(ctx, *, query: str):
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await MusicManager.join(ctx)
    async with ctx.typing():
        players = await MusicManager.create_player(query, ctx.author)

    if players:
        if await MusicManager.queue_add(
            players=players, ctx=ctx
        ) and not await MusicManager.play(ctx):
            embed = discord.Embed(description=":notes: Wow that song has been **added** to the queue!")
            embed.set_footer(text = "Tip: Check the queue with niko queue")
            await ctx.reply(embed=embed, mention_author=False)

    else:
        embed = discord.Embed(description="❌️ Sorry what did you search for?? Nothing with that name/url exists smh.")
        await ctx.reply(embed=embed, mention_author=False)


@bot.command()
async def lyrics(ctx, query: str = None):
    if response := await MusicManager.lyrics(ctx, query):
        title, author, query_lyrics = response

        splitted = query_lyrics.split("\n")
        res = []
        current = ""
        for i, split in enumerate(splitted):
            if len(splitted) <= i + 1 or len(current) + len(splitted[i + 1]) > 1024:
                res.append(current)
                current = ""
                continue
            current += split + "\n"

        page_manager = discordSuperUtils.PageManager(
            ctx,
            [
                discord.Embed(
                    title=f":scroll: Lyrics for '{title}' by '{author}', (Page {i + 1}/{len(res)})",
                    description=x,
                )
                for i, x in enumerate(res)
            ],
            public=True,
        )
        await page_manager.run()
    else:
        embed = discord.Embed(description="❌️ Maybe I'm too dumb but I couldn't find any lyrics for that-")
        await ctx.reply(embed=embed, mention_author=False)


@bot.command()
async def pause(ctx):
    if await MusicManager.pause(ctx):
        embed = discord.Embed(description=":pause_button: I have **paused** your song!")
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def resume(ctx):
    if await MusicManager.resume(ctx):
        embed = discord.Embed(description=":play_pause: **Resuming** your song!")
        await ctx.reply(embed=embed, mention_author=False)
        
@bot.command()
async def stop(ctx):
    song = ctx.voice_client.stop()
    embed = discord.Embed(description="❌️ **Stopped** your song!")
    await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def volume(ctx, volume: int):
    await MusicManager.volume(ctx, volume)


@bot.command()
async def loop(ctx):
    is_loop = await MusicManager.loop(ctx)
    if is_loop is not None:
        embed = discord.Embed(description=f"Looping is now **{is_loop}**")
        await ctx.reply(embed=embed, mention_author=False)


@bot.command()
async def shuffle(ctx):
    if is_shuffle is not None:
        embed = discord.Embed(description=f"Shuffle is now **{is_shuffle}**")
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def autoplay(ctx):
    is_autoplay = await MusicManager.autoplay(ctx)

    if is_autoplay is not None:
        embed = discord.Embed(description=f"*Autoplay is now **{is_autoplay}**")
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def queueloop(ctx):
    if is_loop is not None:
        embed = discord.Embed(description=f"*Queue Looping is now **{is_loop}**")
        await ctx.reply(embed=embed, mention_author=False)


@bot.command()
async def complete_queue(ctx):
    if ctx_queue := await MusicManager.get_queue(ctx):
        formatted_queue = [
            f"Title: '{x.title}'\nRequester: {x.requester and x.requester.mention}\n"
            f"Position: {i - ctx_queue.pos}"
            for i, x in enumerate(ctx_queue.queue)
        ]

        num_of_fields = 25

        embeds = discordSuperUtils.generate_embeds(
            formatted_queue,
            "Complete Song Queue",
            "Shows the complete song queue.",
            num_of_fields,
            string_format="{}",
        )

        page_manager = discordSuperUtils.PageManager(
            ctx, embeds, public=True, index=floor(ctx_queue.pos / 25)
        )
        await page_manager.run()


@bot.command()
async def goto(ctx, position: int):
    if ctx_queue := await MusicManager.get_queue(ctx):
        new_pos = ctx_queue.pos 
        if not 0 <= new_pos < len(ctx_queue.queue):
            embed = discord.Embed(description="Are you dumb fam? That position doesn't exist.")
            await ctx.reply(embed=embed, mention_author=False)
            return

        await MusicManager.goto(ctx, new_pos)
        embed = discord.Embed(description=f"Position moved to **{position}**")
        await ctx.reply(embed=embed, mention_author=False)

@bot.command()
async def skip(ctx, index: int = None):
    await MusicManager.skip(ctx, index)

@bot.command()
async def queue(ctx):
    if ctx_queue := await MusicManager.get_queue(ctx):
        formatted_queue = [
            f"**{x.title}**\nRequested by : {x.requester and x.requester.mention}"
            for x in ctx_queue.queue[0 + 1 :]
        ]

        embeds = discordSuperUtils.generate_embeds(
            formatted_queue,
            ":notes: Queue",
            f"Currently Playing: **{await MusicManager.now_playing(ctx)}**",
            25,
            string_format="{}",
        )

        page_manager = discordSuperUtils.PageManager(ctx, embeds, public=True)
        await page_manager.run()

@bot.command()
async def rewind(ctx, index: int = None):
    await MusicManager.previous(ctx, index, no_autoplay=True)
    
@bot.command()
async def help(ctx):
    embed=discord.Embed(title="🏥 Help Center",description="Please select a category from the list below!")
    msg = await ctx.send(
        embed=embed,
        components = [
            Select(
                placeholder = "Pick a category!",
                options = [
                    SelectOption(label = "🎶️ Music ", value = "See a list of all the music commands!"),
                ]
            )
        ]
    )

    interaction = await bot.wait_for("select_option")
    embed=discord.Embed(title="Music commands",description="Here's a list of all my music commands.")
    embed.add_field(name = ":notes: niko play", value = "Niko play any song you want.")
    embed.add_field(name = ":lock: niko join", value = "Niko joins your VC.")
    embed.add_field(name = "🔓niko leave", value = "Niko leaves your VC.")
    embed.add_field(name = "⏸️ niko pause", value = "Niko pauses the song.")
    embed.add_field(name = "▶️ niko resume", value = "Niko resumes the song.")
    embed.add_field(name = ":loop: niko loop", value = "Niko loops your requested song.")
    embed.add_field(name = ":loop: niko queueloop", value = "Niko loops all songs currently in the queue.")
    embed.add_field(name = " ▶️ niko autoplay", value = "Niko plays the next recommended song.")
    embed.add_field(name = " :scroll: niko queue", value = "Niko shows you the queue.")
    embed.add_field(name = " ❌️ niko skip", value = "Niko skips the currently playing song")
    embed.add_field(name = " 👆️ niko goto", value = "Niko plays a track from the queue based on an integer.")
    embed.add_field(name = " 🔊️ niko volume", value = "Niko changes the volume.")
    embed.add_field(name = " :alarm_clock:  niko np", value = "Niko shows the currently playing song.")
    embed.add_field(name = "🃏️ niko shuffle", value = "Niko plays a random song from the queue.")
    embed.add_field(name = "🛑 niko stop", value = "Niko stops the song.")
    embed.add_field(name = ":abc: niko lyrics", value = "Niko finds lyrics on most songs!")
    embed.add_field(name = "📩 niko invite", value = "Invite niko to other servers!")
    await interaction.edit_origin(embed=embed)

@bot.command()
async def invite(ctx):
    embed=discord.Embed(description="Here are some of my **Related Links!**")
    await ctx.send(
       embed=embed,
        components = [
        [
            Button(label = "📩 Invite me!", url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=66087744&scope=bot", style=5),
            Button(label = "🏨️ Visit Project", url="https://github.com/ZingyTomato/Niko-Music", style=5)
        ]
     ]
    )

bot.run("BOT TOKEN")
