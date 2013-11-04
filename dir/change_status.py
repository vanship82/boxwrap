import collections
import os

from dir import file_entry
from util import util

CONTENT_STATUS_NO_CHANGE = 0
CONTENT_STATUS_FILE_MODIFIED = 1
CONTENT_STATUS_TO_DIR = 2
CONTENT_STATUS_TO_FILE = 3
CONTENT_STATUS_NEW = 4
CONTENT_STATUS_DELETED = 5


class ChangeStatus:

  def __init__(self, path, new_entry, old_entry, content_status,
               parent_change_path=None):
    self.path = path
    self.new_entry = new_entry
    self.old_entry = old_entry
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


def get_change_status(new_entry_list, old_entry_list):
  result = collections.OrderedDict()

  # Pass 1: get content change status
  i_new = iter(new_entry_list)
  i_old = iter(old_entry_list)
  e_new = util.get_next(i_new)
  path_for_sorting_new = e_new.path_for_sorting() if e_new else None
  e_old = util.get_next(i_old)
  path_for_sorting_old = e_old.path_for_sorting() if e_old else None
  top_dir_delete_change_path = None
  while True:
    if path_for_sorting_new == path_for_sorting_old:
      if e_new.is_dir and e_old.is_dir:
        content_status = CONTENT_STATUS_NO_CHANGE
      elif e_new.is_dir and not e_old.is_dir:
        content_status = CONTENT_STATUS_TO_DIR
      elif not e_new.is_dir and e_old.is_dir:
        content_status = CONTENT_STATUS_TO_FILE
      else:
        if (e_new.size == e_old.size and
            e_new.last_modified_time == e_old.last_modified_time):
          content_status = CONTENT_STATUS_NO_CHANGE
        elif (e_new.size != e_old.size or
            e_new.calculate_hash() != e_old.calculate_hash()):
          content_status = CONTENT_STATUS_FILE_MODIFIED
        else:
          content_status = CONTENT_STATUS_NO_CHANGE

      result[e_new.path] = ChangeStatus(
          e_new.path, e_new, e_old, content_status)
      e_new = util.get_next(i_new)
      path_for_sorting_new = e_new.path_for_sorting() if e_new else None
      e_old = util.get_next(i_old)
      path_for_sorting_old = e_old.path_for_sorting() if e_old else None

    elif (path_for_sorting_new is not None and
        (path_for_sorting_new < path_for_sorting_old or
          path_for_sorting_old is None)):
      result[e_new.path] = ChangeStatus(
          e_new.path, e_new, None, CONTENT_STATUS_NEW)
      try:
        e_new = i_new.next()
      except StopIteration:
        e_new = None
      path_for_sorting_new = e_new.path_for_sorting() if e_new else None

    elif (path_for_sorting_old is not None and
        (path_for_sorting_new > path_for_sorting_old or
          path_for_sorting_new is None)):
      result[e_old.path] = ChangeStatus(
          e_old.path, None, e_old, CONTENT_STATUS_DELETED)
      try:
        e_old = i_old.next()
      except StopIteration:
        e_old = None
      path_for_sorting_old = e_old.path_for_sorting() if e_old else None

    # fill parent_change_path
    current_change_path = next(reversed(result))
    current_change = result[current_change_path]
    print current_change_path
    if top_dir_delete_change_path:
      print os.path.relpath(current_change_path, top_dir_delete_change_path)
      if ('..' in
          os.path.relpath(current_change_path, top_dir_delete_change_path)):
        # current change path is in a different dir tree
        top_dir_delete_change_path = None
      else:
        current_change.parent_change_path = top_dir_delete_change_path

    if not top_dir_delete_change_path:
      if (current_change.old_entry and current_change.old_entry.is_dir and
          current_change.content_status in [
            CONTENT_STATUS_DELETED,
            CONTENT_STATUS_TO_FILE]):
        top_dir_delete_change_path = current_change_path


    if e_old is None and e_new is None:
      break

  return result

