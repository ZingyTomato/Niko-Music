# Niko-Music

A free and open source discord bot with no pay-wall. Made using Hikari, Lightbulb and Lavasnek_rs. Supports playing audio from : Spotify, Soundcloud, Twitch, Vimeo and Http Streams. Uses slash commands. 

Invite him to your server!: https://discord.com/api/oauth2/authorize?client_id=915595163286532167&permissions=2213571392&scope=bot%20applications.commands

Docker Image : https://hub.docker.com/r/zingytomato/nikomusic

Support Server : https://discord.gg/grSvEPYtDF

# Deployment with Docker

## Example compose.yml file

```
---
version: "2.1"
services:
  nikomusic:
    image: zingytomato/nikomusic
    container_name: nikomusic
    env_file:
      - .env
    restart: unless-stopped
  lavalink:
    image: zingytomato/lavalink
    container_name: lavalink
    environment: 
      - PASSWORD=nikomusic # Cannot be changed if using both images. For lavalink : https://github.com/ZingyTomato/Niko-Music/tree/main/lavalink
    restart: unless-stopped
```
## .env Example
```
- TOKEN= Discord Bot Token from https://discord.com/developers/applications/
- SPOTCLIENTID= Spotify Client ID from https://developer.spotify.com/dashboard/applications
- SPOTCLIENTSECRET= Spotify Client SECRET from https://developer.spotify.com/dashboard/applications
- GENAPIKEY= Genius Client ID from https://genius.com/api-clients
- LOGGING_SERVER_ID= ID of the discord channel that you want to send logs to
```
