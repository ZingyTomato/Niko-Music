FROM python:3.10-alpine

WORKDIR /niko-music

COPY bot.py bot.py
COPY credentials.py credentials.py
COPY music.py music.py
COPY requirements.txt requirements.txt
COPY functions/ functions/
COPY responses/ responses/

RUN pip3 install -Ur requirements.txt
CMD ["python3", "bot.py"]
