import datetime
import time

import copy
import requests
import slacker
from pip._vendor import colorama


def get_all_from_api_method(method, list_key, desc):
    full_list = []
    next_page = 1
    while True:
        try:
            next_result = method(page=next_page, count=200)
        except (requests.exceptions.HTTPError, slacker.Error) as e:
            print("error getting page {} of {}: {}. Waiting 20 seconds".format(next_page, desc, e))
            time.sleep(20)
            continue
        next_result = next_result.body
        if not next_result['ok'] or not next_result['paging']:
            print("unexpected result from page {} of {}: {}. Waiting 20 seconds.".format(next_page, desc, next_result))
            time.sleep(20)
            continue
        full_list.extend(next_result[list_key])
        page = next_result['paging']['page']
        page_count = next_result['paging']['pages']
        print("Got {} page {} of {}.".format(desc, page, page_count))
        if page < page_count:
            if page != next_page:
                print("Expected page we got to be {}, found {}".format(next_page, page))
            next_page += 1
        else:
            break
    return full_list


class API:
    """
    :type api: slacker.Slacker
    :type channels_by_id: dict[str, dict[str, Any]]
    :type users_by_id: dict[str, dict[str, Any]]
    :type raw_files: list[dict[str, Any]]
    :type files: list[dict[str, Any]]
    :type no_stars_no_pins_files: list[dict[str, Any]]
    """

    def __init__(self, token, file_cache=None):
        """
        :type token: str
        :type file_cache: dict[str, Any]
        """
        self.api = slacker.Slacker(token)
        if file_cache is not None:
            self.channels_by_id = file_cache['channels']
            self.users_by_id = file_cache['users']
            self.raw_files = file_cache['raw_files']
            self.files = file_cache['files']
            self.no_stars_no_pins_files = file_cache['nsnpf']
        else:
            self.channels_by_id = None
            self.users_by_id = None
            self.raw_files = None
            self.files = None
            self.no_stars_no_pins_files = None

    def get_raw_file_list(self):
        if self.raw_files is not None:
            return self.raw_files

        self.raw_files = get_all_from_api_method(self.api.files.list, 'files', 'files list')
        return self.raw_files

    def create_file_cache(self):
        if self.files is not None:
            return
        self.create_channel_cache()
        raw_files = self.get_raw_file_list()
        self.files = []
        self.no_stars_no_pins_files = []

        right_now = datetime.datetime.now(datetime.timezone.utc)
        old_date = (right_now - datetime.timedelta(days=60)).timestamp()
        print("Counting files updated earlier than {} as old enough to be abandoned"
              " (if they are also not starred nor pinned).".format(old_date))

        for file in self.raw_files:
            file = copy.deepcopy(file)
            file['channels'] = [self.channels_by_id.get(channel_id, {}).get('name', channel_id)
                                for channel_id in file['channels']]
            self.files.append(file)
            if file.get('is_public') and not file.get('num_starred') and not file.get('pinned_to') \
                    and file.get('updated', file['created']) < old_date:
                self.no_stars_no_pins_files.append(file)

    def create_channel_cache(self):
        if self.channels_by_id is not None:
            return
        channels = self.api.channels.list(False).body
        if not channels['ok']:
            print(colorama.Fore.RED + "WARNING: Channel list did not return ok!" + colorama.Fore.RESET)
        self.channels_by_id = {}
        for channel in channels['channels']:
            self.channels_by_id[channel['id']] = channel

    def create_user_cache(self):
        if self.users_by_id is not None:
            return
        users = self.api.users.list(False).body
        if not users['ok']:
            print(colorama.Fore.RED + "WARNING: User list did not return ok!" + colorama.Fore.RESET)
        self.users_by_id = {}
        for user in users['members']:
            self.users_by_id[user['id']] = user

    def serialize(self):
        # self.channels_by_id = file_cache['channels']
        # self.users_by_id = file_cache['users']
        # self.raw_files = file_cache['raw_files']
        # self.files = file_cache['files']
        # self.no_stars_no_pins_files = file_cache['nsnpf']
        return {
            'channels': self.channels_by_id,
            'users': self.users_by_id,
            'raw_files': self.raw_files,
            'files': self.files,
            'nsnpf': self.no_stars_no_pins_files
        }
