import collections
import os

from sync import file_info
from util import util

CONTENT_STATUS_UNSPECIFIED = -1
CONTENT_STATUS_NO_CHANGE = 0
CONTENT_STATUS_FILE_MODIFIED = 1
CONTENT_STATUS_TO_DIR = 2
CONTENT_STATUS_TO_FILE = 3
CONTENT_STATUS_NEW = 4
CONTENT_STATUS_DELETED = 5


class ChangeEntry:

  def __init__(self, path, cur_info, old_info, content_status,
               parent_dir_changes=None,
               parent_change_path=None,
               dir_status=CONTENT_STATUS_UNSPECIFIED):
    self.path = path
    self.cur_info = cur_info
    self.old_info = old_info
    self.content_status = content_status
    self.parent_dir_changes = parent_dir_changes
    self.parent_change_path = parent_change_path
    self.dir_status = dir_status

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
        'path: %s, content_status: %s, dir_status: %s%s' % (
            self.path,
            self.content_status,
            self.dir_status,
            (', parent_change: %s' % self.parent_change_path
                if self.parent_change_path else '')))


class DirChanges:

  def __init__(self, base_dir, dir_status, changes, dir_changes_dict):
    self._dir_status = dir_status
    self._changes = changes
    self._changes_dict = {(x.path, x) for x in self._changes}
    self._dir_changes_dict = dir_changes_dict
    self._base_dir = base_dir

  def base_dir(self):
    return self._base_dir

  def dir_status(self):
    return self._dir_status

  def set_dir_status(self, dir_status):
    self._dir_status = dir_status

  def changes(self):
    return self._changes

  def dir_changes(self, dir_path):
    return self._dir_changes_dict[dir_path]

  def flat_changes(self):
    for c in self._changes:
      yield c
      if ((c.cur_info and c.cur_info.is_dir) or
          (c.old_info and c.old_info.is_dir)):
        for sub_c in self._dir_changes_dict[c.path].flat_changes():
          yield sub_c


def get_dir_changes(new_dir_info, old_dir_info, parent_dir_changes=None):
  # TODO: add permission change status
  top_dir_delete_change_path = None
  changes = []
  dir_changes_dict = {}
  base_dir = (new_dir_info.base_dir() if new_dir_info
              else old_dir_info.base_dir())
  cur_dir_changes = DirChanges(base_dir, CONTENT_STATUS_UNSPECIFIED,
                               changes, dir_changes_dict)
  for e_new_info, e_old_info in util.merge_two_iterators(
      iter(new_dir_info.file_info_list() if new_dir_info else []),
      iter(old_dir_info.file_info_list() if old_dir_info else []),
      key_func=lambda x: x.path_for_sorting()):
    dir_status = CONTENT_STATUS_UNSPECIFIED
    if e_new_info and e_old_info:
      if e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      old_dir_info.dir_info(e_old_info.path),
                                      cur_dir_changes)
        dir_changes_dict[e_new_info.path] = dir_changes
        content_status = CONTENT_STATUS_NO_CHANGE
        dir_status = dir_changes.dir_status()
      elif e_new_info.is_dir and not e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None, cur_dir_changes)
        dir_changes_dict[e_new_info.path] = dir_changes
        content_status = CONTENT_STATUS_TO_DIR
        dir_status = dir_changes.dir_status()
      elif not e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes)
        dir_changes_dict[e_new_info.path] = dir_changes
        content_status = CONTENT_STATUS_TO_FILE
        dir_status = dir_changes.dir_status()
      else:
        if e_new_info.is_modified(e_old_info):
          content_status = CONTENT_STATUS_FILE_MODIFIED
        else:
          content_status = CONTENT_STATUS_NO_CHANGE

      path = e_new_info.path
      change = ChangeEntry(
          e_new_info.path, e_new_info, e_old_info, content_status,
          parent_dir_changes=parent_dir_changes, dir_status=dir_status)

    elif e_new_info and not e_old_info:
      path = e_new_info.path
      if e_new_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None,
                                      cur_dir_changes)
        dir_changes_dict[path] = dir_changes
        dir_status = dir_changes.dir_status()

      change = ChangeEntry(
          e_new_info.path, e_new_info, None, CONTENT_STATUS_NEW,
          parent_dir_changes=parent_dir_changes, dir_status=dir_status)

    elif not e_new_info and e_old_info:
      path = e_old_info.path
      if e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      cur_dir_changes)
        dir_changes_dict[path] = dir_changes
        dir_status =dir_changes.dir_status()

      change = ChangeEntry(
          e_old_info.path, None, e_old_info, CONTENT_STATUS_DELETED,
          parent_dir_changes=parent_dir_changes, dir_status=dir_status)

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

    changes.append(change)

    if change.content_status in [CONTENT_STATUS_FILE_MODIFIED,
                                 CONTENT_STATUS_TO_DIR,
                                CONTENT_STATUS_TO_FILE]:
      cur_dir_changes.set_dir_status(CONTENT_STATUS_FILE_MODIFIED)
    elif change.content_status == CONTENT_STATUS_NEW:
      if cur_dir_changes.dir_status() in [CONTENT_STATUS_UNSPECIFIED,
                                          CONTENT_STATUS_NEW]:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_NEW)
      else:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_FILE_MODIFIED)
    elif change.content_status == CONTENT_STATUS_DELETED:
      if cur_dir_changes.dir_status() in [CONTENT_STATUS_UNSPECIFIED,
                                          CONTENT_STATUS_DELETED]:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_DELETED)
      else:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_FILE_MODIFIED)
    else:  # CONTENT_STATUS_NO_CHANGE
      if cur_dir_changes.dir_status() == CONTENT_STATUS_UNSPECIFIED:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_NO_CHANGE)

  return cur_dir_changes


def get_changes(new_dir_info, old_dir_info):
  # TODO: add permission change status
  top_dir_delete_change_path = None
  for e_new_info, e_old_info in util.merge_two_iterators(
      new_dir_info.flat_file_info_list(),
      old_dir_info.flat_file_info_list(),
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


