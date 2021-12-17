from bot import MusicBot
from discord_components import DiscordComponents, ComponentsBot, Button, Select, SelectOption
from discord_slash import cog_ext, SlashContext, SlashCommand

def main():
    bot = MusicBot()
    DiscordComponents(bot)
    slash = SlashCommand(bot, sync_commands=True)
    bot.run()

if __name__ == "__main__":
    main()
