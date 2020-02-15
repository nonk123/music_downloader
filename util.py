import os.path

def ensure_dir_exists(path):
    d = path if os.path.isdir(path) else os.path.split(path)[0]

    if not os.path.exists(d):
        os.makedirs(d, 0o775)

    return path

def flatten_generator(l):
    for e in l:
        if type(e) == list:
            yield from flatten_gen(e)
        else:
            yield e

def flatten(l):
    return [e for e in flatten_generator(l)]

def split_path(path):
    parts = os.path.split(path)

    if parts[0] != "" and parts[1] != "":
        return flatten(split_path(parts[0])) + [parts[1]]
    else:
        return parts[1]
