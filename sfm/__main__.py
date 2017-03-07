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
        if not args.cache_files_result and cache is not None:
            cache['files'] = None
        api = sfm.API(token, cache)
    else:
        api = sfm.API(token)

    api.create_file_cache()

    total_count = len(api.files)
    total_image_count = 0
    total_bytes = 0
    total_image_bytes = 0
    for file in api.files:
        if 'image' in file['mimetype']:
            total_image_count += 1
            total_image_bytes += file['size']
        total_bytes += file['size']

    not_used_count = len(api.no_stars_no_pins_files)
    not_used_image_count = 0
    not_used_bytes = 0
    not_used_image_bytes = 0
    for file in api.no_stars_no_pins_files:
        if 'image' in file['mimetype']:
            not_used_image_count += 1
            not_used_image_bytes += file['size']
        not_used_bytes += file['size']
    print("Found {} files, totaling {} bytes.".format(total_count, total_bytes))
    print("Of those, found {} image files, totaling {} bytes.".format(total_image_count, total_image_bytes))
    print()
    print("Found {} abandoned files, totaling {} bytes.".format(not_used_count, not_used_bytes))
    print("Of those, found {} image files, totaling {} bytes.".format(not_used_image_count, not_used_image_bytes))

    if args.cache:
        with open("screeps-cache.json", mode='w') as f:
            json.dump(api.serialize(), f, indent=4)


run()
