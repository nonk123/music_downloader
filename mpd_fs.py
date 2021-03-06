import os
import os.path

import time

from stat import S_IFDIR, S_IFREG
from fuse import Operations
from sdnotify import SystemdNotifier

from util import ensure_dir_exists, split_path
from config import client

class Cache:
    def __init__(self):
        self.cache_dir = ensure_dir_exists("Cache/")
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
            return len(self.get(track)) if track.is_cached() else 0
        else:
            return 0

    def get(self, track):
        if track:
            return self.read(track) if track.is_cached() else self.download(track)
        else:
            return bytes()

    def read(self, track):
        with open(track.cache_entry, "rb") as file:
            return file.read()

    def download(self, track):
        codec = self.extension[1:]
        bitrate = 192

        track.ym_track.download(ensure_dir_exists(track.cache_entry),
                                codec,
                                bitrate)

        return self.read(track)

cache = Cache()

def contents_getter(fun):
    def wrapper(self, offset=0, length=-1):
        contents = fun(self)
        end = len(contents) if length < 0 else offset + length
        return contents[offset:end]
    return wrapper

class Track:
    def __init__(self, ym_track):
        self.ym_track = ym_track
        self.cache_entry = cache.get_track_path(ym_track)
        self.read_bytes = 0

    def is_cached(self):
        return cache.is_cached(self.ym_track)

    def get_filename(self):
        return cache.get_track_filename(self.ym_track)

    @contents_getter
    def contents(self):
        return cache.get(self)

class DummyFile:
    def __init__(self):
        bitrate = 192000
        sample_rate = 44100

        header = [0xFF, 0xFA, 0xB1, 0x0]

        frame_length = int(144 * bitrate / sample_rate)
        data_length = frame_length - len(header)

        data = [0xA for i in range(data_length)]

        self.frame = header + data
        self.frames = bytes()

        total = 0

        while total < 1024:
            self.frames += bytes(self.frame)
            total += len(self.frame)

        self.real_size = total
        self.fake_size = 8192

    @contents_getter
    def contents(self):
        return self.frames

dummy = DummyFile()

class TracksManager:
    def __init__(self):
        self.artists_file_name = "artists.txt"

    def get_artist_ids(self):
        with open(self.artists_file_name, "r") as f:
            return f.readlines()

    def get_tracks_for_artist_id(self, artist_id):
        artist_id = int(artist_id)
        total = client.artists_tracks(artist_id).pager.total
        return client.artists_tracks(artist_id, 0, total).tracks

    def get_tracks(self):
        for id in self.get_artist_ids():
            yield from self.get_tracks_for_artist_id(id)

class MpdFilesystem(Operations):
    def __init__(self):
        self.tracks_manager = TracksManager()
        self._generate_tree()

    def init(self, path):
        SystemdNotifier().notify("READY=1")

    def _generate_tree(self):
        self.tracks = self.tracks_manager.get_tracks()

        self.tree = {}

        for track in self.tracks:
            for album in track.albums:
                for artist in album.artists:
                    if artist.name not in self.tree:
                        self.tree[artist.name] = {}

                    if album.title not in self.tree[artist.name]:
                        self.tree[artist.name][album.title] = {}

                    self.tree[artist.name][album.title][track.title] = Track(track)

        print("Tree generated")

    def _get_track(self, path):
        parts = split_path(path)
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
        path = split_path(path)

        yield "."
        yield ".."

        if len(path) == 0:
            yield from self._artists()
        elif len(path) == 1:
            yield from self._albums(path[0])
        elif len(path) == 2:
            yield from self._track_filenames(path[0], path[1])

    def _is_dir(self, path):
        return len(split_path(path)) != 3

    def getattr(self, path, fh=None):
        if ".mpdignore" in path:
            return {}

        st = {}

        st["st_uid"] = os.getuid()
        st["st_gid"] = os.getgid()
        st["st_mode"] = S_IFDIR | 0o554 if self._is_dir(path) else S_IFREG | 0o444
        st["st_ctime"] = st["st_mtime"] = st["st_atime"] = time.time()
        st["st_nlink"] = 2 if self._is_dir(path) else 1

        if self._is_dir(path):
            st["st_size"] = 0
        elif self._get_track(path).is_cached():
            st["st_size"] = cache.size(self._get_track(path))
        else:
            st["st_size"] = dummy.fake_size

        return st

    def read(self, path, length, offset, fh):
        if ".mpdignore" in path:
            return bytes()

        if not self._is_dir(path):
            track = self._get_track(path)

            track.read_bytes += offset + length

            if not track.is_cached() and track.read_bytes <= dummy.fake_size * 6:
                return dummy.contents(offset, length)
            else:
                return track.contents(offset, length)
