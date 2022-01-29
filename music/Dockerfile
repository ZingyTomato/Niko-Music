FROM python:3.8-slim-bullseye

WORKDIR /NikoMusic

COPY bot.py bot.py
COPY music_plugin.py music_plugin.py

RUN apt update -y && apt upgrade -y && apt install git -y
RUN pip3 install hikari hikari-lightbulb lavasnek-rs ytmusicapi spotipy uvloop lyricsgenius python-dotenv
RUN pip3 install git+https://github.com/neonjonn/lightbulb-ext-neon.git
CMD ["python3", "bot.py"]
