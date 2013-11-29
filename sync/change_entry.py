import collections
import os

from sync import file_info
from util import util

CONTENT_STATUS_NO_CHANGE = 0
CONTENT_STATUS_FILE_MODIFIED = 1
CONTENT_STATUS_TO_DIR = 2
CONTENT_STATUS_TO_FILE = 3
CONTENT_STATUS_NEW = 4
CONTENT_STATUS_DELETED = 5


class ChangeEntry:

  def __init__(self, path, cur_info, old_info, content_status,
               parent_change_path=None):
    self.path = path
    self.cur_info = cur_info
    self.old_info = old_info
    self.content_status = content_status
    self.parent_change_path = parent_change_path

  def to_csv(self):
    output = cStringIO.StringIO()
    writer = i18n.UnicodeWriter(output)
    writer.writerow([
      self.path,
      self.content_status,
      self.parent_change_path])
    return output.getvalue().strip('\r\n')

  def __str__(self):
    return (
        'path: %s, content_status: %s, %s' % (
            self.path,
            self.content_status,
            ('parent_change: %s' % self.parent_change_path
                if self.parent_change_path else '')))


def get_changes(new_dir_info, old_dir_info):
  # TODO: add permission change status
  top_dir_delete_change_path = None
  for e_new_info, e_old_info in util.merge_two_iterators(
      iter(new_dir_info.file_info_list()),
      iter(old_dir_info.file_info_list()),
      key_func=lambda x: x.path_for_sorting()):
    if e_new_info and e_old_info:
      if e_new_info.is_dir and e_old_info.is_dir:
        content_status = CONTENT_STATUS_NO_CHANGE
      elif e_new_info.is_dir and not e_old_info.is_dir:
        content_status = CONTENT_STATUS_TO_DIR
      elif not e_new_info.is_dir and e_old_info.is_dir:
        content_status = CONTENT_STATUS_TO_FILE
      else:
        if e_new_info.is_modified(e_old_info):
          content_status = CONTENT_STATUS_FILE_MODIFIED
        else:
          content_status = CONTENT_STATUS_NO_CHANGE

      path = e_new_info.path
      change = ChangeEntry(
          e_new_info.path, e_new_info, e_old_info, content_status)

    elif e_new_info and not e_old_info:
      path = e_new_info.path
      change = ChangeEntry(
          e_new_info.path, e_new_info, None, CONTENT_STATUS_NEW)

    elif not e_new_info and e_old_info:
      path = e_old_info.path
      change = ChangeEntry(
          e_old_info.path, None, e_old_info, CONTENT_STATUS_DELETED)

    # fill parent_change_path
    if top_dir_delete_change_path:
      if '..' in os.path.relpath(path, top_dir_delete_change_path):
        # current change path is in a different dir tree
        top_dir_delete_change_path = None
      else:
        change.parent_change_path = top_dir_delete_change_path

    if not top_dir_delete_change_path:
      if (change.old_info and change.old_info.is_dir and
          change.content_status in [
              CONTENT_STATUS_DELETED,
              CONTENT_STATUS_TO_FILE]):
        top_dir_delete_change_path = path

    yield path, change


