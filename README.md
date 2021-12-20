# Niko-Music

A free and open source discord bot with no pay-wall. Made using lavalink, discord.py, discord-components, lyricsgenius, and Carabera's tutorial series on Youtube. Can play audio from Soundcloud, Bandcamp, Twitch and Vimeo! Defaults to Soundcloud. Just type `niko help` in a server to find out more!

## Installation Instructions

### Install Required Dependencies

`pip3 install discord.py[voice] discord-components discord-py-slash-command lyricsgenius wavelink`

### Clone the repository 

` git clone https://github.com/ZingyTomato/Niko-Music.git && cd Niko-Music `

### Values to change

In `bot.py`, replace 'Bot Token' with your Discord Bot Token

![image](https://user-images.githubusercontent.com/79736973/146800132-a759f91b-ab23-4917-90a2-3a6bc8181157.png)

In `bot.py` and `music.py`, replace the existing channel id with the id of the channel that you want to send logs in.

![image](https://user-images.githubusercontent.com/79736973/146800248-b1998744-75af-4962-935f-5eea0c896a74.png)

In `music.py`, replace GENIUS API KEY with the key you get from here : http://genius.com/api-clients

![image](https://user-images.githubusercontent.com/79736973/146800764-0bb75ca1-b5dc-437a-b1fa-5d22c50fa8a2.png)

Finally, in `music.py`, replace the invite URL with your bot's invite URL.

![image](https://user-images.githubusercontent.com/79736973/146800875-2499a93e-643c-40b4-9a47-232e311d4d95.png)

### Bring the bot up

`python3 launcher.py`

