# Media_Manager
Simple Python/Notion Media Management Application (Work in progress)

Mount the drive first:

```
sudo mount -v -t cifs //mediacenter.local/volume -o guest /media/MediaCenter
sudo mount -t nfs -o mountvers=3 bacchus.local:/Multimedia /media/Qnap
sshfs -v cola@bacchus.local:/share/Multimedia /media/Qnap/Multimedia/
```

Neue Filme auf Wotan
Backup auf Qnap

Logik:

- neues, watchlist -> fritzNAS
- klassiker, top 250 -> MediaCenter


TODOs:
- Es war einmal in Amerika (Wotan - 2teiler) vs. fritzNAS - Einteiler
- Der Pate (Wotan, 2teiler)
- Fehlende IMDB_IDs einfüllen z.B. König der Löwen: imdb_id (tt0110357) eintragen
- Hitparade Erotik-Filme von: https://www.imdb.com/filmosearch/?role=nm0086471

/media/Qnap/Multimedia/share/Multimedia/Videos/Movies
