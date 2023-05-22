# Shows-Sorter
An automated sorter (Rename/Sort/Manage Database)
WORK IN PROGRESS
<hr>
<h1> Presentation </h1>
This server allow you to manage your Anime/Show/Movie. Here is a list of what it can do
<ul>
  <li>create directories according to metadata from <a href="https://www.themoviedb.org/">TheMovieDataBase</a> (including seasons)</li>
  <li>Move episode according to there title to the right directory</li>
  <li>Can download torrent from rss feeds, filter on words can be applied</li>
  <li>provide an API to manage the database from program or website (a web UI is being built <a href="https://github.com/Strange500/Shows-Sorter/tree/test">here</a>)</li>
  <li>will be able to suuport directories from Google drive</li>
</ul>
<hr>
<h1>Installation</h1>
you will need python 3.8 or newer, you will need several depencies<br>
<code>pip install  feedparser, psutil, requests, tmdbsimple, flask, flask_cors, pymediainfo
</code>
<br> <p> You will need to correctly configure the server, download server.conf and replace path according to instructions in (directories are not created automatically please create them before starting server (server will crash otherwise)</p> <br>
<p>By default the server stock its data on windows in <code>AppData\Local\my-server</code> and on Linux <code>/var/lib/my-server</code>. But you can change it by changing <code>VAR_DIR</code> in lib.py by the path you want
