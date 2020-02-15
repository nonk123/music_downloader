#!/usr/bin/python3

from fuse import FUSE

from config import client, artists_of_interest
from mpd_fs import MpdFilesystem

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
        return None, []

def all_tracks():
    for id in artists_of_interest():
        artist, tracks = artist_exists(id)

        if artist:
            yield from tracks

def main():
    FUSE(MpdFilesystem(all_tracks()), "Music/", nothreads=True, foreground=True)

if __name__ == "__main__":
    main()
