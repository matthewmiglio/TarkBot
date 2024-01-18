import time
from os import makedirs
from os.path import exists, expandvars, join
import os


module_name = "py-tarkbot"

top_level = join(expandvars("%appdata%"), module_name)
log_folder_path = join(top_level, "logs")


LOG_FILE_CAP = 10


def make_new_log_dir():
    # if there are more than 10 logs, delete the oldest one
    while count_log_files() > LOG_FILE_CAP - 1:
        # print(f"Deleting oldest log file bc we're beyond capacity: {LOG_FILE_CAP}")
        try:
            delete_oldest_date()
        except:
            print("Failed to delete oldest log file")

    name = f"Tarkbot log  {get_current_date()}  #{time.time()}.txt"
    path = os.path.join(log_folder_path, name)
    make_empty_file(path)
    print(f'Made new log file: "{path}"')

    return path


def make_folder(location):
    if not exists(location):
        makedirs(location)
        return True
    return False


def get_current_date():
    from datetime import datetime

    now = datetime.now()
    return now.strftime("%m-%d-%Y")


def make_empty_file(location):
    if not exists(location):
        f = open(location, "w")
        f.close()


def check_if_logs_folder_exists():
    return exists(log_folder_path)


def make_logs_folder():
    make_folder(log_folder_path)
    print("Made empty logs folder!")


def get_times_of_all_logs():
    times = []
    names = os.listdir(log_folder_path)
    for name in names:
        date = name.split("#")[1].replace(".txt", "")
        times.append(date)

    return times


def get_oldest_date():
    dates = get_times_of_all_logs()
    dates.sort()
    return dates[0]


def delete_oldest_date():
    date = get_oldest_date()
    names = os.listdir(log_folder_path)
    for name in names:
        if date in name:
            path = os.path.join(log_folder_path, name)
            os.remove(path)
            print(f"Deleted {path}")
            return True

    return False


def add_line_to_log_file(path, text):
    f = open(path, "a")
    f.write(text + "\n")
    f.close()


def count_log_files():
    return len(os.listdir(log_folder_path))


# do file check upon import
if make_folder(top_level):
    print("Made tarkbot folder in appdata")

if not check_if_logs_folder_exists():
    make_logs_folder()

