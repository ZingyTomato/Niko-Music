import os
import hikari
import lightbulb

bot = lightbulb.BotApp(token="TOKEN")

@bot.listen()
async def starting_load_extensions(_: hikari.StartingEvent) -> None:
    bot.load_extensions("music_plugin")

@bot.listen()
async def on_ready(_: hikari.StartedEvent):
    guilds = await bot.rest.fetch_my_guilds()
    await bot.update_presence(status=hikari.Status.ONLINE, activity=hikari.Activity(type=hikari.ActivityType.PLAYING, name=f"/help in {len(guilds)} servers!"))

@bot.command()
@lightbulb.command("ping", "See Niko's latency.")
@lightbulb.implements(lightbulb.SlashCommand)
async def ping(ctx: lightbulb.Context) -> None:
    embed=hikari.Embed(title=f"My ping is {bot.heartbeat_latency * 1_000:.0f} ms", color=0xD7CBCC)
    await ctx.respond(embed=embed)


if os.name != "nt":
    import uvloop
    uvloop.install()

bot.run()
