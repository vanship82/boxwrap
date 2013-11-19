import collections
import os
import random
import shutil

from sync import change_entry
from sync import file_info
from util import util


class SyncChangeEntry:

  def __init__(self, change, tmp_file):
    self.change = change
    self.tmp_file = tmp_file


class SyncFileInfo:

  def __init__(self, file_info, tmp_file):
    self.file_info = file_info
    self.tmp_file = tmp_file


# return random file name
def _copy_to_tmp_dir(path, tmp_dir):
  while True:
    random_file_name = '%032x' % random.getrandbits(128)
    full_file_name = os.path.join(tmp_dir, random_file_name)
    if not os.path.exists(full_file_name):
      break

  shutil.copyfile(path, full_file_name)
  return random_file_name


# Generate SyncChangeEntry one-way from src directory to dest_dir_info
def generate_sync_changes(src, dest_dir_info, tmp_dir):
  old_cwd = os.getcwd()
  os.chdir(src)
  src_dir_info = file_info.load_dir_info('.')
  os.chdir(old_cwd)
  for path, change in change_entry.get_changes(src_dir_info, dest_dir_info):
    tmp_file = None
    if (change.content_status ==
        change_entry.CONTENT_STATUS_FILE_MODIFIED):
      tmp_file = _copy_to_tmp_dir(os.path.join(src, change.cur_info.path),
                                  tmp_dir)
    elif change.content_status == change_entry.CONTENT_STATUS_TO_FILE:
      tmp_file = _copy_to_tmp_dir(os.path.join(src, change.cur_info.path),
                                  tmp_dir)
    elif change.content_status == change_entry.CONTENT_STATUS_NEW:
      if not change.cur_info.is_dir:
        tmp_file = _copy_to_tmp_dir(os.path.join(src, change.cur_info.path),
                                    tmp_dir)
    yield path, SyncChangeEntry(change, tmp_file)


def apply_sync_change_to_file_info(sync_change):
  change = sync_change.change
  if change.parent_change_path:
    # This file is already deleted as the parent change path is deleted
    return None
  elif change.content_status == change_entry.CONTENT_STATUS_DELETED:
    return None

  return SyncFileInfo(change.cur_info, sync_change.tmp_file)

