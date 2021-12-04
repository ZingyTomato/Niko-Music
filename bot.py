import asyncio
import nextcord
import youtube_dl
import nextcord
from nextcord.ext import commands
import json
import lyricsgenius
import os 
import subprocess
import shlex

# Suppress noise about console usage from errors

youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Get audio using youtube-dl

class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist	
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Main music cog

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command()
    async def stream(self, ctx, *, url):
      async with ctx.typing():
      	player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
      	ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
      	cmd=shlex.split(f'youtube-dl "ytsearch:{url}" --get-thumbnail')
      	cmd2=shlex.split(f'youtube-dl "ytsearch:{url}" --get-duration')
      	img = subprocess.check_output(cmd)
      	img2 = subprocess.check_output(cmd2)
      	finalimg = img.decode('utf-8')
      	finaldur = img2.decode('utf-8')
      	embed=nextcord.Embed(description=f"**Currently Playing!**", color = nextcord.Color.green())
      	embed.add_field(name = "Title", value =f"{player.title}", inline = False)
      	embed.add_field(name = "Length", value =f"{finaldur}", inline = False)
      	embed.set_image(url=finalimg)
      	await ctx.reply(embed=embed,mention_author=False)
    @commands.command()
    async def pause(self, ctx):
        song = ctx.voice_client.pause()
        embed=nextcord.Embed(description=f"I've **paused** the currently playing song!", color = nextcord.Color.red())
        await ctx.reply(embed=embed, mention_author=False)
    @commands.command()
    async def resume(self, ctx):
        song = ctx.voice_client.resume()
        embed=nextcord.Embed(description=f"Resuming...", color = nextcord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)
    @commands.command()
    async def leave(self, ctx):
        voicetrue = ctx.author.voice
        myvoicetrue = ctx.guild.me.voice
        if voicetrue is None:
            embed=nextcord.Embed(description="You have not **joined** a voice channel!", color = nextcord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)
        if myvoicetrue  is None:
            embed=nextcord.Embed(description="I am not currently **in** a voice channel!", color = nextcord.Color.red())
            return await ctx.reply(embed=embed, mention_author=False)
        await ctx.voice_client.disconnect()
        embed=nextcord.Embed(description=f"I have **left** your voice channel!", color = nextcord.Color.green())
        await ctx.reply(embed=embed, mention_author=False)
    @commands.command()
    async def stop(self, ctx):
        song = ctx.voice_client.stop()
        embed=nextcord.Embed(description=f"I've **stopped** the song!", color = nextcord.Color.red())
        await ctx.reply(embed=embed, mention_author=False)
    @commands.command()
    async def join(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                embed=nextcord.Embed(description=f"I am now **in** your voice channel!", color = nextcord.Color.green())
       	        await ctx.reply(embed=embed, mention_author=False)
            else:
                embed=nextcord.Embed(description=f"You are not **in** a voice channel! Kindly join one.", color = nextcord.Color.red())
                await ctx.reply(embed=embed, mention_author=False)
                
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

# Set bot prefix

bot = commands.Bot(command_prefix=commands.when_mentioned_or("niko "), help_command=None)

# Change bot status

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.listening, name="niko help"))
    
class HelpDropdown(nextcord.ui.Select):
    def __init__(self):
        SelectOptions = [
            nextcord.SelectOption(label="🎵 Music", description="See a list of all the Music commands!")
            ]
        super().__init__(placeholder="Choose a category", min_values=1, max_values=1, options=SelectOptions)

    async def callback(self, interaction: nextcord.Interaction):
        if self.values[0] == '🎵 Music':
            embed=nextcord.Embed(title="Music commands",description="Here's a list of all my music commands.", color = nextcord.Colour.green())
            embed.add_field(name = "niko stream", value = "Play any song you want (A URL is not required).  **Example : niko stream never gonna give you up**")
            embed.add_field(name = "niko join", value = "Joins a voice channel")
            embed.add_field(name = "niko leave", value = "Stops the currently playing song and leaves the voice channel")
            embed.add_field(name = "niko pause", value = "Pauses the currently playing song/audio.")
            embed.add_field(name = "niko resume", value = "Resumes the currently playing song/audio.")
            embed.add_field(name = "niko stop", value = "Stops the currently playing song/audio.")
            embed.add_field(name = "niko lyrics", value = "Find lyrics on your desired songs!")
            embed.add_field(name = "niko invite", value = "Invite me to other servers!")
            return await interaction.response.edit_message(embed=embed)

class DropdownView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=10.0)
        self.add_item(HelpDropdown())
    async def on_timeout(self):
        self.children[0].disabled = True
        await self.message.edit(view=self)

# Help command

@bot.command()
@commands.cooldown(5, 30, commands.BucketType.user)
async def help(ctx):
    author_id = ctx.author.id
    embed=nextcord.Embed(title="Help Center",description="Please select a category from the list below!")
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
    view = DropdownView()
    view.message = await ctx.reply(embed=embed, view=view, mention_author=False)
    
# Lyrics command.
 
@bot.command()
@commands.cooldown(5, 30, commands.BucketType.user)
async def lyrics(ctx, *, title):
    genius = lyricsgenius.Genius("TOKEN")
    genius.verbose = False
    genius.remove_section_headers = True
    genius.skip_non_songs = True
    song = genius.search_song(f"{title}")
    embed=nextcord.Embed(title=f"Lyrics for {title}!" ,description=f"{song.lyrics}")
    await ctx.reply(embed=embed, mention_author=False)
  
# Invite command 
 
@bot.command()
@commands.cooldown(5, 30, commands.BucketType.user)
async def invite(ctx):
	yes = nextcord.ui.View()
	yes.add_item(nextcord.ui.Button(label="Invite me!", url="https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=66087744&scope=bot"))
	embed=nextcord.Embed(description="Here's my invite link!")
	await ctx.reply(embed=embed,mention_author=False, view=yes)

# Error Handling

@lyrics.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed=nextcord.Embed(title="You gotta be kidding me",description = "What song's lyrics do you want??", color=nextcord.Colour.red())
        await ctx.reply(embed=embed, mention_author=False)

bot.add_cog(Music(bot))
bot.run('TOKEN')
