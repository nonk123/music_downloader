import os.path

def ensure_dir_exists(path):
    d = path if os.path.isdir(path) else os.path.split(path)[0]

    if not os.path.exists(d):
        os.makedirs(d, 0o775)

    return path

def split_path(path):
    parts = os.path.split(path)

    if "" in parts:
        return []
    elif parts[0] in ("", "/"):
        return [parts[1]]
    elif parts[1] == "":
        return [parts[0]]
    else:
        return split_path(parts[0]) + [parts[1]]
