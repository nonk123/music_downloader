#!/usr/bin/python3

from config import client

def process(track):
    artist = track.artists[0].name
    album = track.albums[0].title
    title = track.title

    print("%s - %s - %s" % (artist, album, title))

def artist_exists(id):
    try:
        artist = client.artists_tracks(id)
        total = artist.pager.total

        tracks = []

        per_page = 20
        page = 0

        while total > per_page:
            tracks += client.artists_tracks(id, page, per_page).tracks
            page += 1
            total -= per_page

        tracks += client.artists_tracks(id, page, total).tracks

        return artist, tracks
    except BaseException as e:
        print(e)
        return False, []

def main():
    for id in range(1, 10):
        artist, tracks = artist_exists(id)
        if artist:
            for track in tracks:
                process(track)
            print()

if __name__ == "__main__":
    main()
