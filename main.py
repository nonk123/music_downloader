#!/usr/bin/python3

from fuse import FUSE
from mpd_fs import MpdFilesystem
from util import ensure_dir_exists

if __name__ == "__main__":
    FUSE(MpdFilesystem(), ensure_dir_exists("Music/"), foreground=True)
