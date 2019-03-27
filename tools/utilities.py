import wx
from db.sql_connector import DVH_SQL
from datetime import datetime
from dateutil.parser import parse as parse_date
import numpy as np
from os import walk, listdir
from os.path import join, isfile
import os
import shutil


def get_file_paths(start_path, search_subfolders=False):
    if os.path.isdir(start_path):
        if search_subfolders:
            file_paths = []
            for root, dirs, files in walk(start_path, topdown=False):
                for name in files:
                    file_paths.append(join(root, name))
            return file_paths

        return [join(start_path, f) for f in listdir(start_path) if isfile(join(start_path, f))]
    return []

def get_study_instance_uids(**kwargs):
    cnx = DVH_SQL()
    uids = {table: cnx.get_unique_values(table, 'study_instance_uid', condition) for table, condition in kwargs.items()}
    cnx.close()

    complete_list = flatten_list_of_lists(list(uids.values()), remove_duplicates=True)

    uids['common'] = [uid for uid in complete_list if is_uid_in_all_keys(uid, uids)]
    uids['unique'] = complete_list

    return uids


def is_uid_in_all_keys(uid, uids):
    key_answer = {}
    # Initialize a False value for each key
    for key in list(uids):
        key_answer[key] = False
    # search for uid in each keyword fof uid_kwlist
    for key, value in uids.items():
        if uid in value:
            key_answer[key] = True

    final_answer = True
    # Product of all answer[key] values (except 'unique')
    for key, value in key_answer.items():
        if key not in 'unique':
            final_answer *= value
    return final_answer


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    data = [item for sublist in some_list for item in sublist]
    if sort:
        data.sort()
    if remove_duplicates:
        return list(set(data))
    return data


def collapse_into_single_dates(x, y):
    """
    :param x: a list of dates in ascending order
    :param y: a list of values as a function of date
    :return: a unique list of dates, sum of y for that date, and number of original points for that date
    :rtype: dict
    """

    # average daily data and keep track of points per day
    x_collapsed = [x[0]]
    y_collapsed = [y[0]]
    w_collapsed = [1]
    for n in range(1, len(x)):
        if x[n] == x_collapsed[-1]:
            y_collapsed[-1] = (y_collapsed[-1] + y[n])
            w_collapsed[-1] += 1
        else:
            x_collapsed.append(x[n])
            y_collapsed.append(y[n])
            w_collapsed.append(1)

    return {'x': x_collapsed, 'y': y_collapsed, 'w': w_collapsed}


def moving_avg(xyw, avg_len):
    """
    :param xyw: a dictionary of of lists x, y, w: x, y being coordinates and w being the weight
    :param avg_len: average of these number of points, i.e., look-back window
    :return: list of x values, list of y values
    """
    cumsum, moving_aves, x_final = [0], [], []

    for i, y in enumerate(xyw['y'], 1):
        cumsum.append(cumsum[i - 1] + y / xyw['w'][i - 1])
        if i >= avg_len:
            moving_ave = (cumsum[i] - cumsum[i - avg_len]) / avg_len
            moving_aves.append(moving_ave)
    x_final = [xyw['x'][i] for i in range(avg_len - 1, len(xyw['x']))]

    return x_final, moving_aves


def convert_value_to_str(value, round=2):
    try:
        formatter = "%%0.%df" % round
        return formatter % value
    except TypeError:
        return value


def get_selected_listctrl_items(list_control):
    selection = []

    index_current = -1
    while True:
        index_next = list_control.GetNextItem(index_current, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index_next == -1:
            return selection

        selection.append(index_next)
        index_current = index_next


def print_run_time(start_time, end_time, calc_title):
    total_time = end_time - start_time
    seconds = total_time.seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        print("%s. This took %dhrs %02dmin %02dsec to complete" % (calc_title, h, m, s))
    elif m:
        print("%s. This took %02dmin %02dsec to complete" % (calc_title, m, s))
    else:
        print("%s. This took %02dsec to complete" % (calc_title, s))


def datetime_str_to_obj(datetime_str):
    """
    :param datetime_str: a string representation of a datetime as formatted in DICOM (YYYYMMDDHHMMSS)
    :return: a datetime object
    :rtype: datetime
    """

    year = int(datetime_str[0:4])
    month = int(datetime_str[4:6])
    day = int(datetime_str[6:8])
    hour = int(datetime_str[8:10])
    minute = int(datetime_str[10:12])
    second = int(datetime_str[12:14])

    datetime_obj = datetime(year, month, day, hour, minute, second)

    return datetime_obj


def date_str_to_obj(date_str):
    """
    :param date_str: a string representation of a date as formatted in DICOM (YYYYMMDD)
    :return: a datetime object
    :rtype: datetime
    """

    year = int(date_str[0:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    return datetime(year, month, day)


def datetime_to_date_string(datetime_obj):
    if isinstance(datetime_obj, str):
        datetime_obj = parse_date(datetime_obj)
    return "%s/%s/%s" % (datetime_obj.month, datetime_obj.day, datetime_obj.year)


def change_angle_origin(angles, max_positive_angle):
    """
    :param angles: a list of angles
    :param max_positive_angle: the maximum positive angle, angles greater than this will be shifted to negative angles
    :return: list of the same angles, but none exceed the max
    :rtype: list
    """
    if len(angles) == 1:
        if angles[0] > max_positive_angle:
            return [angles[0] - 360]
        else:
            return angles
    new_angles = []
    for angle in angles:
        if angle > max_positive_angle:
            new_angles.append(angle - 360)
        elif angle == max_positive_angle:
            if angle == angles[0] and angles[1] > max_positive_angle:
                new_angles.append(angle - 360)
            elif angle == angles[-1] and angles[-2] > max_positive_angle:
                new_angles.append(angle - 360)
            else:
                new_angles.append(angle)
        else:
            new_angles.append(angle)
    return new_angles


def calc_stats(data):
    """
    :param data: a list or numpy 1D array of numbers
    :return: a standard list of stats (max, 75%, median, mean, 25%, and min)
    :rtype: list
    """
    data = [x for x in data if x != 'None']
    try:
        data_np = np.array(data)
        rtn_data = [np.max(data_np),
                    np.percentile(data_np, 75),
                    np.median(data_np),
                    np.mean(data_np),
                    np.percentile(data_np, 25),
                    np.min(data_np)]
    except:
        rtn_data = [0, 0, 0, 0, 0, 0]
        print("calc_stats() received non-numerical data")
    return rtn_data


def move_files_to_new_path(files, new_dir):
    for file_path in files:
        file_name = os.path.basename(file_path)
        new = os.path.join(new_dir, file_name)
        try:
            shutil.move(file_path, new)
        except:
            os.mkdir(new_dir)
            shutil.move(file_path, new)


# def remove_empty_folders(start_path):
#     if start_path[0:2] == './':
#         rel_path = start_path[2:]
#         start_path = os.path.join(SCRIPT_DIR, rel_path)
#
#     for (path, dirs, files) in os.walk(start_path, topdown=False):
#         if files:
#             continue
#         try:
#             if path != start_path:
#                 os.rmdir(path)
#         except OSError:
#             pass


def move_all_files(new_dir, old_dir):
    """
    This function will move all files from the old to new directory, it will ignore all files in subdirectories
    :param new_dir: absolute directory path
    :param old_dir: absolute directory path
    """
    initial_path = os.path.dirname(os.path.realpath(__file__))

    os.chdir(old_dir)

    file_paths = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]

    misc_path = os.path.join(new_dir, 'misc')
    if not os.path.isdir(misc_path):
        os.mkdir(misc_path)

    for f in file_paths:
        file_name = os.path.basename(f)
        new = os.path.join(misc_path, file_name)
        shutil.move(f, new)

    os.chdir(initial_path)
