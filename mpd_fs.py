import os
import os.path

import time

from stat import S_IFDIR, S_IFREG
from fuse import Operations

import util

class Cache:
    def __init__(self):
        self.cache_dir = util.ensure_dir_exists("Cache/")
        self.extension = ".mp3"

    def get_track_path(self, ym_track):
        artist = ym_track.artists[0].name
        album = ym_track.albums[0].title
        filename = self.get_track_filename(ym_track)

        return os.path.join(self.cache_dir, artist, album, filename)

    def get_track_filename(self, ym_track):
        return ym_track.title + self.extension

    def is_cached(self, ym_track):
        return os.path.exists(self.get_track_path(ym_track))

    def size(self, track):
        if track:
            return len(self.get(track)) if track.cached else 0
        else:
            return 0

    def get(self, track):
        if track:
            return self.read(track) if track.cached else self.download(track)
        else:
            return bytearray()

    def read(self, track):
        with open(track.cache_entry, "rb") as file:
            return file.read()

    def download(self, track):
        codec = self.extension[1:]
        bitrate = 192

        track.ym_track.download(util.ensure_dir_exists(track.cache_entry),
                                codec,
                                bitrate)

        track.cached = True

        return self.read(track)

cache = Cache()

class Track:
    def __init__(self, ym_track):
        self.ym_track = ym_track
        self.cached = cache.is_cached(ym_track)
        self.cache_entry = cache.get_track_path(ym_track)

    def get_filename(self):
        return cache.get_track_filename(self.ym_track)

    def contents(self):
        return cache.get(self)

class MpdFilesystem(Operations):
    def __init__(self, tracks):
        self.tracks = tracks
        self._generate_tree()

    def _generate_tree(self):
        self.tree = {}

        for track in self.tracks:
            for album in track.albums:
                for artist in album.artists:
                    if artist.name not in self.tree:
                        self.tree[artist.name] = {}

                    if album.title not in self.tree[artist.name]:
                        self.tree[artist.name][album.title] = {}

                    self.tree[artist.name][album.title][track.title] = Track(track)

    def _get_track(self, path):
        parts = util.split_path(path)

        if ".mpdignore" in parts:
            return None
        else:
            return self.tree[parts[0]][parts[1]][os.path.splitext(parts[2])[0]]

    def _artists(self):
        for k, v in self.tree.items():
            yield k

    def _albums(self, artist):
        for k, v in self.tree[artist].items():
            yield k

    def _tracks(self, artist, album):
        for k, v in self.tree[artist][album].items():
            yield k, v

    def _track_filenames(self, artist, album):
        for _, track in self._tracks(artist, album):
            yield cache.get_track_filename(track.ym_track)

    def readdir(self, path, fh):
        path = util.split_path(path)

        yield "."
        yield ".."

        if len(path) == 0:
            yield from self._artists()
        elif len(path) == 1:
            yield from self._albums(path[0])
        elif len(path) == 2:
            yield from self._track_filenames(path[0], path[1])

    def _is_dir(self, path):
        return len(util.split_path(path)) != 3

    def getattr(self, path, fh=None):
        st = {}

        st["st_uid"] = os.getuid()
        st["st_gid"] = os.getgid()
        st["st_mode"] = S_IFDIR | 0o554 if self._is_dir(path) else S_IFREG | 0o444
        st["st_ctime"] = st["st_mtime"] = st["st_atime"] = time.time()
        st["st_nlink"] = 2 if self._is_dir(path) else 1
        st["st_size"] = 0 if self._is_dir(path) else cache.size(self._get_track(path))

        return st

    def read(self, path, length, offset, fh):
        if not self._is_dir(path):
            track = self._get_track(path)

            if track:
                return track.contents()[offset : offset + length]
            else:
                return bytearray()
