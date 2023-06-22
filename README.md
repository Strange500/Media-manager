# Shows-Sorter
An automated sorter (Rename/Sort/Manage Database)
WORK IN PROGRESS
[![CodeFactor](https://www.codefactor.io/repository/github/strange500/media-manager/badge)](https://www.codefactor.io/repository/github/strange500/media-manager)
<hr>

# Presentation

This server allows you to manage your Anime/Show/Movie collection. Here is a list of what it can do:

- Create directories according to metadata from [TheMovieDataBase](https://www.themoviedb.org/) (including seasons)
- Move episodes according to their title to the right directory
- Download torrents from RSS feeds, with the ability to apply word filters
- Provide an API to manage the database programmatically or through a website (a web UI is being built [here](https://github.com/Strange500/Shows-Sorter/tree/test))
- Will be able to support directories from Google Drive

<hr>

# Installation

You will need Python 3.8 or newer, as well as several dependencies. Run the following command to install them:

```bash
pip install feedparser psutil requests tmdbsimple flask flask_cors pymediainfo 
```

You will also need to correctly configure the server. Download `server.conf` and replace the paths according to the instructions. Please note that directories are not created automatically, so make sure to create them before starting the server (otherwise, the server will crash).

By default, the server stores its data on Windows in `AppData\Local\my-server` and on Linux in `/var/lib/my-server`. However, you can change this by modifying the `VAR_DIR` variable in `lib.py` with the desired path.


