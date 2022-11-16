# Niko-Music

A free and open source discord bot with no pay-wall. Made using discord.py and wavelink.

Invite the bot to your server!: https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2163239168&scope=bot%20applications.commands

Docker Image : https://hub.docker.com/r/zingytomato/nikomusic

Support Server : https://discord.gg/grSvEPYtDF

## Local Development

Clone the Repository
```sh
$ git clone https://github.com/ZingyTomato/Niko-Music
```
Enter `/Niko-Music` and install all the requirements using
```sh
$ pip3 install -Ur requirements.txt
```
Fill in [`.env`](https://github.com/ZingyTomato/Niko-Music/blob/main/niko-music/.env) with all the appropiate info. (Check the file)

Run the bot using
```sh
$ python3 niko-music/bot.py
```

## Deployment with Docker

Check out both the [`docker-compose.yml`](https://github.com/ZingyTomato/Niko-Music/blob/main/docker-compose.yml) and [`.env`](https://github.com/ZingyTomato/Niko-Music/blob/main/niko-music/.env) files which are required to deploy the stack.
