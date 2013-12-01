import collections
import os
import random
import shutil

from sync import file_info
from util import util

CONTENT_STATUS_UNSPECIFIED = -1
CONTENT_STATUS_NO_CHANGE = 0
CONTENT_STATUS_MODIFIED = 1
CONTENT_STATUS_TO_DIR = 2
CONTENT_STATUS_TO_FILE = 3
CONTENT_STATUS_NEW = 4
CONTENT_STATUS_DELETED = 5


class ChangeEntry:

  def __init__(self, path, cur_info, old_info, content_status,
               parent_dir_changes=None,
               dir_status=CONTENT_STATUS_UNSPECIFIED):
    self.path = path
    self.cur_info = cur_info
    self.old_info = old_info
    self.content_status = content_status
    self.parent_dir_changes = parent_dir_changes
    self.dir_status = dir_status

  def parent_change_path(self):
    if self.content_status != CONTENT_STATUS_DELETED:
      return None
    dir_changes = self.parent_dir_changes
    parent_change_path = None
    while (dir_changes is not None
           and dir_changes.dir_status() == CONTENT_STATUS_DELETED):
      parent_change_path = dir_changes.base_dir()
      dir_changes = dir_changes.parent_dir_changes()
    return parent_change_path

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
        'path: %s, content_status: %s, dir_status: %s, tmp_file: %s%s' % (
            self.path,
            self.content_status,
            self.dir_status,
            self.cur_info.tmp_file if self.cur_info else None,
            (', parent_change: %s' % self.parent_change_path()
                if self.parent_change_path() else '')))


class DirChanges:

  def __init__(self, base_dir, dir_status, changes=None, dir_changes_dict=None,
               parent_dir_changes=None):
    self._dir_status = dir_status
    self._changes = changes or []
    self._changes_dict = dict([(x.path, x) for x in self._changes])
    self._dir_changes_dict = dir_changes_dict or {}
    self._base_dir = base_dir
    self._parent_dir_changes = parent_dir_changes

  def base_dir(self):
    return self._base_dir

  def dir_status(self):
    return self._dir_status

  def set_dir_status(self, dir_status):
    self._dir_status = dir_status

  def add_change(self, change):
    self._changes.append(change)
    self._changes_dict[change.path] = change

  def changes(self):
    return self._changes

  def change(self, path):
    return self._changes_dict[path]

  def put_dir_changes(self, dir_path, dir_changes):
    self._dir_changes_dict[dir_path] = dir_changes

  def dir_changes(self, dir_path):
    return self._dir_changes_dict[dir_path]

  def parent_dir_changes(self):
    return self._parent_dir_changes

  def flat_changes(self):
    for c in self._changes:
      yield c
      if ((c.cur_info and c.cur_info.is_dir) or
          (c.old_info and c.old_info.is_dir)):
        for sub_c in self._dir_changes_dict[c.path].flat_changes():
          yield sub_c


# return random file name
def _copy_to_tmp_dir(root_dir, path, tmp_dir):
  while True:
    random_file_name = '%032x' % random.getrandbits(128)
    full_file_name = os.path.join(tmp_dir, random_file_name)
    if not os.path.exists(full_file_name):
      break

  shutil.copyfile(os.path.join(root_dir, path), full_file_name)
  return random_file_name


def get_dir_changes(new_dir_info, old_dir_info, parent_dir_changes=None,
                    root_dir=None, tmp_dir=None):
  # TODO: add permission change status
  top_dir_delete_change_path = None
  base_dir = (new_dir_info.base_dir() if new_dir_info
              else old_dir_info.base_dir())
  cur_dir_changes = DirChanges(base_dir, CONTENT_STATUS_UNSPECIFIED,
                               parent_dir_changes=parent_dir_changes)
  for e_new_info, e_old_info in util.merge_two_iterators(
      iter(new_dir_info.file_info_list() if new_dir_info else []),
      iter(old_dir_info.file_info_list() if old_dir_info else []),
      key_func=lambda x: x.path_for_sorting()):
    dir_status = CONTENT_STATUS_UNSPECIFIED
    tmp_file = None
    if e_new_info and e_old_info:
      if e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        cur_dir_changes.put_dir_changes(e_new_info.path, dir_changes)
        content_status = CONTENT_STATUS_NO_CHANGE
        dir_status = dir_changes.dir_status()
      elif e_new_info.is_dir and not e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None, parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        cur_dir_changes.put_dir_changes(e_new_info.path, dir_changes)
        content_status = CONTENT_STATUS_TO_DIR
        dir_status = dir_changes.dir_status()
      elif not e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        cur_dir_changes.put_dir_changes(e_new_info.path, dir_changes)
        content_status = CONTENT_STATUS_TO_FILE
        dir_status = dir_changes.dir_status()
        if root_dir and tmp_dir:
          tmp_file = _copy_to_tmp_dir(root_dir, e_new_info.path, tmp_dir)
      else:
        if e_new_info.is_modified(e_old_info):
          content_status = CONTENT_STATUS_MODIFIED
          if root_dir and tmp_dir:
            tmp_file = _copy_to_tmp_dir(root_dir, e_new_info.path, tmp_dir)
        else:
          content_status = CONTENT_STATUS_NO_CHANGE

      path = e_new_info.path
      if tmp_file:
        e_new_info = file_info.copy_with_tmp_file(e_new_info, tmp_file)
      change = ChangeEntry(
          e_new_info.path, e_new_info, e_old_info, content_status,
          parent_dir_changes=cur_dir_changes, dir_status=dir_status)

    elif e_new_info and not e_old_info:
      path = e_new_info.path
      if e_new_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None, parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        cur_dir_changes.put_dir_changes(path, dir_changes)
        dir_status = dir_changes.dir_status()
      elif root_dir and tmp_dir:
        tmp_file = _copy_to_tmp_dir(root_dir, e_new_info.path, tmp_dir)
        if tmp_file:
          e_new_info = file_info.copy_with_tmp_file(e_new_info, tmp_file)

      change = ChangeEntry(
          e_new_info.path, e_new_info, None, CONTENT_STATUS_NEW,
          parent_dir_changes=cur_dir_changes, dir_status=dir_status)

    elif not e_new_info and e_old_info:
      path = e_old_info.path
      if e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        cur_dir_changes.put_dir_changes(path, dir_changes)
        dir_status =dir_changes.dir_status()

      change = ChangeEntry(
          e_old_info.path, None, e_old_info, CONTENT_STATUS_DELETED,
          parent_dir_changes=cur_dir_changes, dir_status=dir_status)

    cur_dir_changes.add_change(change)

    if change.content_status in [CONTENT_STATUS_MODIFIED,
                                 CONTENT_STATUS_TO_DIR,
                                CONTENT_STATUS_TO_FILE]:
      cur_dir_changes.set_dir_status(CONTENT_STATUS_MODIFIED)
    elif change.content_status == CONTENT_STATUS_NEW:
      if cur_dir_changes.dir_status() in [CONTENT_STATUS_UNSPECIFIED,
                                          CONTENT_STATUS_NEW]:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_NEW)
      else:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_MODIFIED)
    elif change.content_status == CONTENT_STATUS_DELETED:
      if cur_dir_changes.dir_status() in [CONTENT_STATUS_UNSPECIFIED,
                                          CONTENT_STATUS_DELETED]:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_DELETED)
      else:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_MODIFIED)
    else:  # CONTENT_STATUS_NO_CHANGE
      if cur_dir_changes.dir_status() == CONTENT_STATUS_UNSPECIFIED:
         cur_dir_changes.set_dir_status(CONTENT_STATUS_NO_CHANGE)

  return cur_dir_changes


def apply_dir_changes_to_dir_info(base_dir, dir_changes):
  file_info_list = []
  for change in dir_changes.flat_changes():
    if change.parent_change_path():
      # This file is already deleted as the parent change path is deleted
      continue
    elif change.content_status == CONTENT_STATUS_DELETED:
      continue
    fi = change.cur_info
    file_info_list.append(change.cur_info)
  return file_info.load_dir_info_from_file_info_list(base_dir, file_info_list)

