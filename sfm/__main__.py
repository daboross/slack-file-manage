import argparse
import json

import sfm


def run():
    parser = argparse.ArgumentParser(description='Retrieve and manipulate slack files.')
    parser.add_argument('--token', dest='token', action='store', metavar='TOKEN', type=str, nargs=1,
                        default=None, help='the slack token, will try to read .screeps-token otherwise')
    parser.add_argument('--cache', dest='cache', action='store_true', default=False,
                        help='cache intermediate results in screeps-cache.json')
    parser.add_argument('--no-file-cache', dest='cache_files_result', action='store_false', default=True,
                        help='when caching, disables caching files and only caches raw results')

    args = parser.parse_args()

    if args.token is not None:
        token = args.token
    else:
        with open(".screeps-token") as f:
            token = f.read().strip()

    if args.cache:
        try:
            with open("screeps-cache.json") as f:
                cache = json.load(f)
        except FileNotFoundError:
            cache = None
        if not args.cache_files_result:
            del cache['files']
        api = sfm.API(token, cache)
    else:
        api = sfm.API(token)

    api.create_file_cache()
    count = 0
    bytes = 0
    for file in api.no_stars_no_pins_files:
        count += 1
        bytes += file['size']
    print("Found {} total files, {} abandoned files, totaling {} bytes.".format(len(api.files), count, bytes))

    if args.cache:
        with open("screeps-cache.json", mode='w') as f:
            json.dump(api.serialize(), f, indent=4)


run()
