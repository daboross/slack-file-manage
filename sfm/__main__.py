import argparse
import json
from pathlib import Path

import os

import sfm


def run():
    parser = argparse.ArgumentParser(description='Retrieve and manipulate slack files.')
    parser.add_argument('--token', dest='token', action='store', metavar='TOKEN', type=str, nargs=1,
                        default=None, help='the slack token, will try to read .screeps-token otherwise')
    parser.add_argument('--cache', dest='cache', action='store_true', default=False,
                        help='cache intermediate results in screeps-cache.json')
    parser.add_argument('--no-file-cache', dest='cache_files_result', action='store_false', default=True,
                        help='when caching, disables caching files and only caches raw results')
    parser.add_argument('--download-files', dest='download_files', action='store_true', default=False,
                        help='if used, download all files into ./downloads/ and create a ./downloads/files.json file containing metadata.')
    parser.add_argument('--delete-abandoned-images', dest='delete_abandoned_images', action='store_true', default=False,
                        help='if used, send delete commands for all abandoned image files!')

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
        else:
            print("Loaded cache.")
            if not args.cache_files_result:
                cache['files'] = None
        api = sfm.API(token, cache)
    else:
        api = sfm.API(token)

    api.create_file_cache()

    total_count = len(api.files)
    total_image_count = 0
    total_bytes = 0
    total_image_bytes = 0
    total_private_count = 0
    total_private_bytes = 0
    for file in api.files:
        if 'image' in file['mimetype']:
            total_image_count += 1
            total_image_bytes += file['size']
        if not file.get('is_public'):
            total_private_count += 1
            total_private_bytes += file['size']
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
    print("Of files, found {} image files, totaling {} bytes.".format(total_image_count, total_image_bytes))
    print("Of files, found {} private files, totaling {} bytes.".format(total_private_count, total_private_bytes))
    print()
    print("Found {} abandoned files, totaling {} bytes.".format(not_used_count, not_used_bytes))
    print("Of those, found {} image files, totaling {} bytes.".format(not_used_image_count, not_used_image_bytes))

    if args.cache:
        print("Writing cache.")
        with open("screeps-cache.json", mode='w') as f:
            json.dump(api.serialize(), f, indent=4)

    if args.download_files:
        root_path = Path(os.getcwd()).joinpath('downloads')
        print("Downloading to {}.".format(root_path))
        try:
            root_path.mkdir(mode=0o755, parents=True)
        except FileExistsError:
            pass
        file_info_dict = {}
        total = len(api.files)
        for index, file_obj in enumerate(api.files):
            file_filename = file_obj['id']
            if 'updated' in file_filename:
                file_filename += 'updated-{}'.format(file_filename['updated'])
            file_filename += os.path.splitext(file_obj['name'])[1]
            file_obj['relative_file_path'] = file_filename
            file_info_dict[file_filename] = file_obj

            target_path = root_path.joinpath(file_filename)
            if target_path.exists():
                with target_path.open('rb') as f:
                    is_empty = len(f.read(1)) <= 0
                if not is_empty:
                    print("[{}/{}] Skipping {}.".format(index + 1, total, target_path))
                    continue
            print("Downloading {} ({}) to {}.".format(file_obj['id'], file_obj['name'], target_path))
            with target_path.open('wb') as f:
                contents = api.get_file_contents_iter(file_obj)
                if contents is not None:
                    for block in contents:
                        f.write(block)
                else:
                    print("{} is a gist or google docs file, writing URL instead.".format(file_filename))
                    f.write(file_obj['url_private'].encode())
            print("[{}/{}] Finished {}.".format(index + 1, total, file_filename))
        downloads_files_path = root_path.joinpath('files.json')
        print("Writing {}.".format(downloads_files_path))
        with downloads_files_path.open('w') as f:
            json.dump(file_info_dict, f)

    if args.delete_abandoned_images:
        mime_types = set()
        image_ids = []
        total_bytes = 0
        earliest_creation = None
        latest_creation = None
        for file in api.no_stars_no_pins_files:
            if 'image' not in file['mimetype']:
                continue
            mime_types.add(file['mimetype'])
            if earliest_creation is None or file['created'] < earliest_creation:
                earliest_creation = file['created']
            if latest_creation is None or file['created'] > latest_creation:
                latest_creation = file['created']
            total_bytes += file['size']
            image_ids.append(file['id'])
        print("""
--------------------------
WARNING: WILL DELETE FILES
--------------------------
File stats:
\tAll mime types: {mime_types}
\tTotal count: {count}
\tEarliest created date: {earliest}
\tLatest created date: {latest}
\tTotal bytes: {bytes}
--------------------------
To delete the above files, enter "delete"
--------------------------""".format(mime_types=mime_types,
                                     count=len(image_ids),
                                     earliest=earliest_creation,
                                     latest=latest_creation,
                                     bytes=total_bytes))
        result = input('> ')
        if result == 'delete':
            print("--------------"
                  "\nDELETING FILES"
                  "\n--------------")
            for image_id in image_ids:
                print(image_id)
                api.api.files.delete(image_id)
        else:
            print("Did not enter 'delete', exiting.")


run()
