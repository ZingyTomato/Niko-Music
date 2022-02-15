FROM python:3.8-slim-bullseye

WORKDIR /NikoMusic

COPY bot.py bot.py
COPY music_plugin.py music_plugin.py

RUN apt update -y && apt upgrade -y && apt install wget -y
RUN wget https://raw.githubusercontent.com/ZingyTomato/Niko-Music/main/requirements.txt
RUN pip3 install -Ur requirements.txt
CMD ["python3", "bot.py"]
