class Functions: ## Contains common functions.
    async def format_duration(self, time):
        return self.strftime("%M:%S", self.gmtime(time)) ## Returns the time in MM:SS.
    
    async def get_track(self, guild):
        return self.wavelink.NodePool.get_node().get_player(guild).track ## Returns info about the current track.

    async def get_player(self, guild):
        return self.wavelink.NodePool.get_node().get_player(guild) ## Returns player info.

    async def get_queue(self, guild):
        return self.wavelink.NodePool.get_node().get_player(guild).queue._queue ## Returns the queue.

    async def shuffle(self, queue):
        return self.random.shuffle(queue) ## Shuffles the queue.

    async def gather_track_info(self, title, artist, track_info): ## Use info from spotify to modify existing track_info.
        search_results = self.spotify.search(q=f"{title} {artist}", limit=1) ## Search spotify for metadata.
        track_info.title = search_results['tracks']['items'][0]['name']
        track_info.title_url = search_results['tracks']['items'][0]['external_urls']['spotify']
        track_info.author = search_results['tracks']['items'][0]['artists'][0]['name']
        track_info.author_url = search_results['tracks']['items'][0]['artists'][0]['external_urls']['spotify']
        track_info.album = search_results['tracks']['items'][0]['album']['name']
        track_info.album_url = search_results['tracks']['items'][0]['album']['external_urls']['spotify']
        track_info.cover_url = search_results['tracks']['items'][0]['album']['images'][0]['url']
        track_info.release_date = search_results['tracks']['items'][0]['album']['release_date']
        return track_info

    async def gather_track_info_cached(self, track_info, track_metadata): ## Use info from existing spotify results to avoid many requests. Used in /url for tracks.
        track_info.title = track_metadata['name']
        track_info.title_url = track_metadata['external_urls']['spotify']
        track_info.author = track_metadata['artists'][0]['name']
        track_info.author_url = track_metadata['artists'][0]['external_urls']['spotify']
        track_info.album = track_metadata['album']['name']
        track_info.album_url = track_metadata['album']['external_urls']['spotify']
        track_info.cover_url = track_metadata['album']['images'][0]['url']
        track_info.release_date = track_metadata['album']['release_date']
        return track_info

    async def modify_volume(self, guild, volume: int):
        player = await self.get_player(guild) ## Retrieve the player.
        return await player.set_volume(volume) ## Change the volume.

    async def remove_track(self, queue, track_index: int):
        return queue.__delitem__(track_index -1) ## Remove the track from the queue. 1 is subtracted as the queue starts from 0.

    async def skipto_track(self, guild, track_index: int):
        player = await self.get_player(guild) ## Retrieve the player.
        queue = await self.get_queue(guild) ## Retrieve the queue.
        player.queue.put_at_front(queue[track_index - 1]) ## Place the requested track at the front of the queue.
        return queue.__delitem__(track_index) ## Remove the track from the queue.

    async def get_new_releases(self):
        tracks = self.spotify.new_releases(limit=10) ## Returns 10 newly released tracks from spotify.
        return tracks

    async def get_trending(self):
        return self.spotify.playlist_tracks(self.trending_uri, limit=10) ## Returns 10 tracks in the trending playlist.

    async def playlist_info(self, playlist_url):
        playlist_id = playlist_url.split("/")[-1].split("?")[0] ## Returns only the playlist ID.
        return self.spotify.playlist(playlist_id) ## Returns info about the playlist.

    async def album_info(self, album_url):
        album_id = album_url.split("/")[-1].split("?")[0] ## Returns only the album ID.
        return self.spotify.album(album_id) ## Returns info about the album.

    async def add_spotify_url(self, guild, media_url, channel_id, url_type): ## Adds either a spotify playlist or album to the queue.
        media_id = media_url.split("/")[-1].split("?")[0] ## Returns only the playlist ID.
        player = await self.get_player(guild) ## Retrieve the player.
            
        if not hasattr(player, 'reply'): ## Check whether or not the guild's player contains certain values.
            player.reply = channel_id ## Define the same values as in the play command since the player attributes do not exist yet.
            player.loop = False 
            player.queue_loop = False 
            player.looped_track = None 
            player.queue_looped_track = None 
        else: ## Otherwise, ignore.
            pass

        if url_type == "playlist":
            try:
                media_tracks = self.spotify.playlist_tracks(media_id) ## Used to retrieve all tracks in a playlist.
            except self.spot_exception: ## If nothing was found, return none.
                return None
        
        elif url_type == "album":
            try:
                media_tracks = self.spotify.album_tracks(media_id) ## Used to retrieve all tracks in an album.
            except self.spot_exception: ## If nothing was found, return none.
                return None

        for i, track in enumerate(media_tracks["items"], start=0): ## Loop through all tracks in the playlist/album.
            
            if i == 1 and not await self.get_track(guild): ## If the first track has been added to queue and nothing else is currently playing.
                next_track = await player.queue.get_wait()  ## Retrieve the queue.
                await player.play(next_track) ## Immediatley play the first track to avoid waiting for the entire queue to be loaded.
                player.looped_track = next_track 
            
            try:
                title = track["track"]["name"]
                artist = track["track"]["artists"][0]["name"]
            except KeyError: ## Spotify albums have different paths.
                title = track["name"]
                artist = track["artists"][0]["name"]

            track_name = f"{title} {artist}" ## Collect the track name and artist name from spotify.

            try:
                media = await self.wavelink.YouTubeMusicTrack.search(
                    track_name, return_first=True) ## Search for the song in the playlist.
            except IndexError: ## If no results were found, skip to the next track.
                pass
            
            final_track = await self.gather_track_info(media.title, 
            media.author, media) ## Modify the playlist track info with spotify before adding to the queue.

            await player.queue.put_wait(final_track) ## Add the playlist/album to the queue.
        return True ## Return true to avoid conflicts with SpotifyException.

    async def add_track(self, guild, track_url, channel_id): ## Adds a spotify track to the queue.
        track_id = track_url.split("/")[-1].split("?")[0] ## Returns only the track ID.
        player = await self.get_player(guild) ## Retrieve the player.
        queue = await self.get_queue(guild) ## Retreieve the queue.

        if not hasattr(player, 'reply'): ## Check whether or not the guild's player contains certain values.
            player.reply = channel_id ## Define the same values as in the play command since the player attributes do not exist yet.
            player.loop = False 
            player.queue_loop = False 
            player.looped_track = None 
            player.queue_looped_track = None 
        else: ## Otherwise, ignore.
            pass

        try:
            track_info = self.spotify.track(track_id) ## Retrieve track info.
        except self.spot_exception: ## If nothing was found, return none.
            return None

        title = track_info['name']
        artist = track_info["artists"][0]["name"]
        track_name = f"{title} {artist}" ## Collect the track name and artist name from spotify.

        try:
            track = await self.wavelink.YouTubeMusicTrack.search(
                track_name, return_first=True) ## Search for the song.
        except IndexError: ## If no results were found, pass.
            pass
        
        final_track = await self.gather_track_info_cached(track, track_info) ## Modify the track info with existing spotify info before adding to the queue.
                
        if await self.get_track(guild): ## If something is currently playing, add the track to the queue. 
            await player.queue.put_wait(final_track) ## Add the track to the queue.
            return final_track ## Return the track info required for the added to queue embed.
        
        else: ## Otherwise play it now.
            await player.play(final_track)
            return final_track ## Return the track info required for the added to queue embed.

    async def get_lyrics(self, search_query: str):
        track = self.genius.search_song(search_query) ## Search for lyrics.
        
        try:
            return track.lyrics.split("\n",1)[1] ## Delete the first line to remove genius junk.
        except (AttributeError, IndexError): ## If no lyrics were found.
            return "No lyrics found!"

    async def search_songs(self, search_query: str):
        search_results = self.spotify.search(q=f'{search_query}', limit=10) ## Returns 10 results from spotify.
        return search_results

    async def format_search_results(self, search_results):
        return f"\n".join(
            [f"**{i}.** [{track['name']}]({track['external_urls']['spotify']}) - [{track['album']['name']}]({track['album']['external_urls']['spotify']}) - [{track['artists'][0]['name']}]({track['artists'][0]['external_urls']['spotify']})" 
            for i, track in enumerate(search_results['tracks']['items'], start=1)]) ## Returns the data in a Title:Album:Artist format.