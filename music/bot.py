import os
import hikari
import lightbulb
import dotenv
import miru
from lightbulb.ext import tasks

dotenv.load_dotenv()

bot = lightbulb.BotApp(os.getenv("TOKEN"))
miru.load(bot)
tasks.load(bot)

@bot.listen()
async def starting_load_extensions(_: hikari.StartingEvent) -> None:
    bot.load_extensions("music_plugin")

@tasks.task(s=60)
async def on_ready():
    guilds = await bot.rest.fetch_my_guilds()
    await bot.update_presence(status=hikari.Status.ONLINE, activity=hikari.Activity(type=hikari.ActivityType.PLAYING, name=f"/help in {len(guilds)} servers!"))

@bot.command()
@lightbulb.command("ping", "See Niko's latency.", auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title=f"My ping is {bot.heartbeat_latency * 1_000:.0f} ms.", color=0x6100FF)
    await ctx.respond(embed=embed)


if os.name != "nt":
    import uvloop
    uvloop.install()

on_ready.start()
bot.run()
