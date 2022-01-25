FROM python:3.8-slim-bullseye

WORKDIR /NikoMusic

COPY music/ music/

RUN mkdir musicfiles
RUN apt update -y && apt upgrade -y
RUN apt install git youtube-dl -y
RUN pip3 install hikari hikari-lightbulb lavasnek-rs ytmusicapi spotipy uvloop lyricsgenius 
RUN pip3 install git+https://github.com/neonjonn/lightbulb-ext-neon.git
CMD ["python3", "music/bot.py"]

