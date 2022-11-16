FROM python:3.10-alpine

COPY niko-music/bot.py bot.py
COPY niko-music/credentials.py credentials.py
COPY niko-music/music.py music.py
COPY requirements.txt requirements.txt
COPY niko-music/functions/ functions/
COPY niko-music/responses/ responses/

RUN pip3 install -Ur requirements.txt
CMD ["python3", "bot.py"]
