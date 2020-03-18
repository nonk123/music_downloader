#!/usr/bin/python3

from fuse import FUSE

from mpd_fs import MpdFilesystem

import util

def main():
    fs = MpdFilesystem()
    FUSE(fs, util.ensure_dir_exists("Music/"), foreground=True)

if __name__ == "__main__":
    main()
