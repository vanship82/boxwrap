import collections

from dir import file_entry

CONTENT_STATUS_NO_CHANGE = 0
CONTENT_STATUS_FILE_MODIFIED = 1
CONTENT_STATUS_TO_DIR = 2
CONTENT_STATUS_TO_FILE = 3
CONTENT_STATUS_NEW = 4
CONTENT_STATUS_DELETED = 5


class ChangeStatus:

  def __init__(self, path, new_entry, old_entry, content_status):
    self.path = path
    self.new_entry = new_entry
    self.old_entry = old_entry
    self.content_status = content_status


def get_change_status(new_entry_list, old_entry_list):
  result = collections.OrderedDict()

  # Pass 1: get content change status
  i_new = iter(new_entry_list)
  i_old = iter(old_entry_list)
  try:
    e_new = i_new.next()
  except StopIteration:
    e_new = None
  path_for_sorting_new = e_new.path_for_sorting() if e_new else None
  try:
    e_old = i_old.next()
  except StopIteration:
    e_old = None
  path_for_sorting_old = e_old.path_for_sorting() if e_old else None
  while True:
    print 'new: ' + (e_new.path if e_new else 'None')
    print 'old: ' + (e_old.path if e_old else 'None')
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
      try:
        e_new = i_new.next()
      except StopIteration:
        e_new = None
      path_for_sorting_new = e_new.path_for_sorting() if e_new else None
      try:
        e_old = i_old.next()
      except StopIteration:
        e_old = None
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

    if e_old is None and e_new is None:
      break

  return result

