import collections
import os
import random
import shutil

import compression
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
               dir_changes=None, parent_dir_changes=None,
               conflict_info=None):
    self.path = path
    self.cur_info = cur_info
    self.old_info = old_info
    self.content_status = content_status
    self.dir_changes = dir_changes
    self.parent_dir_changes = parent_dir_changes
    self.conflict_info = conflict_info

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

  def dir_status(self):
    if not self.dir_changes:
      return CONTENT_STATUS_UNSPECIFIED
    return self.dir_changes.dir_status()

  def __str__(self):
    return (
        'path: %s, content_status: %s, dir_status: %s, tmp_file: %s%s' % (
            self.path,
            self.content_status,
            self.dir_status(),
            self.cur_info.tmp_file if self.cur_info else None,
            (', parent_change: %s' % self.parent_change_path()
                if self.parent_change_path() else '')))


class DirChanges:

  def __init__(self, base_dir, dir_status, changes=None,
               parent_dir_changes=None):
    self._dir_status = dir_status
    self._changes = changes or []
    self._changes_dict = dict([(x.path, x) for x in self._changes])
    self._base_dir = base_dir
    self._parent_dir_changes = parent_dir_changes

  def base_dir(self):
    return self._base_dir

  def dir_status(self):
    if self._dir_status == CONTENT_STATUS_UNSPECIFIED:
      # This only happens when dir is empty.
      return CONTENT_STATUS_NO_CHANGE
    return self._dir_status

  def add_change(self, change):
    self._changes.append(change)
    self._update_dir_status_by_change(change)
    self._changes_dict[change.path] = change

  def changes(self):
    return self._changes

  def change(self, path):
    return self._changes_dict[path]

  def dir_changes(self, path):
    return self._changes_dict[path].dir_changes

  def parent_dir_changes(self):
    return self._parent_dir_changes

  def flat_changes(self):
    for c in self._changes:
      yield c
      if ((c.cur_info and c.cur_info.is_dir) or
          (c.old_info and c.old_info.is_dir)):
        for sub_c in c.dir_changes.flat_changes():
          yield sub_c

  def _update_dir_status_by_change(self, change):
    if change.content_status in [CONTENT_STATUS_MODIFIED,
                                 CONTENT_STATUS_TO_DIR,
                                 CONTENT_STATUS_TO_FILE]:
      self._dir_status = CONTENT_STATUS_MODIFIED
    elif change.content_status == CONTENT_STATUS_NEW:
      if self._dir_status in [CONTENT_STATUS_UNSPECIFIED,
                              CONTENT_STATUS_NEW]:
         self._dir_status = CONTENT_STATUS_NEW
      else:
         self._dir_status = CONTENT_STATUS_MODIFIED
    elif change.content_status == CONTENT_STATUS_DELETED:
      if self._dir_status in [CONTENT_STATUS_UNSPECIFIED,
                                          CONTENT_STATUS_DELETED]:
         self._dir_status = CONTENT_STATUS_DELETED
      else:
         self._dir_status = CONTENT_STATUS_MODIFIED
    else:  # CONTENT_STATUS_NO_CHANGE
      if self._dir_status == CONTENT_STATUS_UNSPECIFIED:
         self._dir_status = CONTENT_STATUS_NO_CHANGE


# return random file name
def _copy_to_tmp_dir(root_dir, path, tmp_dir):
  random_file_name = generate_tmp_file(tmp_dir)
  full_file_name = os.path.join(tmp_dir, random_file_name)
  # TODO: guard that if path has been deleted or changed to dir,
  # maybe just create a placeholder tmp_file
  shutil.copy2(os.path.join(root_dir, path), full_file_name)
  return random_file_name


def generate_tmp_file(tmp_dir):
  while True:
    random_file_name = '%032x' % random.getrandbits(128)
    full_file_name = os.path.join(tmp_dir, random_file_name)
    if not os.path.exists(full_file_name):
      return random_file_name


# root_dir is the root for new_dir_info
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
    dir_changes = None
    if e_new_info and e_old_info:
      if e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        if dir_changes.dir_status() == CONTENT_STATUS_NO_CHANGE:
          content_status = CONTENT_STATUS_NO_CHANGE
        else:
          content_status = CONTENT_STATUS_MODIFIED
        dir_status = dir_changes.dir_status()
      elif e_new_info.is_dir and not e_old_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None, parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        content_status = CONTENT_STATUS_TO_DIR
        dir_status = dir_changes.dir_status()
      elif not e_new_info.is_dir and e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
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
      if (not e_new_info.compressed_file_info
          and e_old_info.compressed_file_info
          and content_status == CONTENT_STATUS_NO_CHANGE):
        e_new_info.compressed_file_info = e_old_info.compressed_file_info
      if (not e_new_info.original_file_info
          and e_old_info.original_file_info
          and content_status == CONTENT_STATUS_NO_CHANGE):
        e_new_info.original_file_info = e_old_info.original_file_info
      if tmp_file:
        e_new_info = file_info.copy_with_tmp_file(e_new_info, tmp_file, tmp_dir)
      change = ChangeEntry(
          e_new_info.path, e_new_info, e_old_info, content_status,
          dir_changes=dir_changes, parent_dir_changes=cur_dir_changes)

    elif e_new_info and not e_old_info:
      path = e_new_info.path
      if e_new_info.is_dir:
        dir_changes = get_dir_changes(new_dir_info.dir_info(e_new_info.path),
                                      None, parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        dir_status = dir_changes.dir_status()
      elif root_dir and tmp_dir:
        tmp_file = _copy_to_tmp_dir(root_dir, e_new_info.path, tmp_dir)
        if tmp_file:
          e_new_info = file_info.copy_with_tmp_file(e_new_info, tmp_file,
                                                    tmp_dir)

      change = ChangeEntry(
          e_new_info.path, e_new_info, None, CONTENT_STATUS_NEW,
          dir_changes=dir_changes, parent_dir_changes=cur_dir_changes)

    elif not e_new_info and e_old_info:
      path = e_old_info.path
      if e_old_info.is_dir:
        dir_changes = get_dir_changes(None,
                                      old_dir_info.dir_info(e_old_info.path),
                                      parent_dir_changes=cur_dir_changes,
                                      root_dir=root_dir, tmp_dir=tmp_dir)
        dir_status = dir_changes.dir_status()

      change = ChangeEntry(
          e_old_info.path, None, e_old_info, CONTENT_STATUS_DELETED,
          dir_changes=dir_changes, parent_dir_changes=cur_dir_changes)

    cur_dir_changes.add_change(change)

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


def _generate_conflict_copy_path(path, count):
  dirname, basename = os.path.split(path)
  splits = basename.split('.')
  if len(splits) > 1:
    return os.path.join(
        dirname,
        '.'.join(splits[:-1]) + ' (conflict copy %s).%s' % (count ,splits[-1]))
  else:
    return os.path.join(dirname, basename + ' (conflict copy %s)' %  count)


def _get_conflict_copy_path(full_path):
  count = 1
  while (True):
    conflict_copy_path = compression.generate_conflict_copy_path(
        full_path, count)
    if not os.path.exists(conflict_copy_path):
      return conflict_copy_path
    count += 1


CONFLICT_NO_CONFLICT = 1
CONFLICT_NEW = 2
CONFLICT_DEST = 3


def _get_file_conflict_state(change, full_path, force_conflict):
  if os.path.isdir(full_path):
    return CONFLICT_NEW
  elif force_conflict:
    return force_conflict
  elif os.path.isfile(full_path):
    fi = file_info.load_file_info(full_path)
    if ((change.old_info and not change.old_info.is_modified(fi)) or
        (change.cur_info and not change.cur_info.is_modified(fi)) or
        (change.conflict_info and not change.conflict_info.is_modified(fi))):
      return CONFLICT_NO_CONFLICT
    else:
      # Keep the dest unchanged, because it may be opened
      return CONFLICT_NEW
  else:
    # No exist
    return CONFLICT_NO_CONFLICT


def _get_dir_conflict_state(change, full_path):
  if os.path.isdir(full_path):
    return CONFLICT_NO_CONFLICT
  elif os.path.isfile(full_path):
    if change.content_status == CONTENT_STATUS_DELETED:
      # Maybe both CONFLICT_NEW and CONFLICT_DEST are OK?
      return CONFLICT_NEW
    else:
      # Change the dest unchanged, because it is hard to rename dir
      return CONFLICT_DEST
  else:
    return CONFLICT_NO_CONFLICT


def apply_dir_changes_to_dir(dest_dir, dir_changes, force_conflict=None):
  for c in dir_changes.changes():
    full_path = os.path.join(dest_dir, c.path)
    if c.content_status == CONTENT_STATUS_TO_FILE:
      if not os.path.exists(full_path):
        c.cur_info.copy_tmp(full_path)
      elif os.path.isdir(full_path):
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                 force_conflict=force_conflict)
        if os.listdir(full_path):
          # Conflict, the directory still exists
          c.cur_info.copy_tmp(_get_conflict_copy_path(full_path))
        else:
          os.rmdir(full_path)
          c.cur_info.copy_tmp(full_path)
      else:
        # full_path is a file
        if c.cur_info.is_modified(file_info.load_file_info(full_path)):
          # Conflict, the existing file is changed
          c.cur_info.copy_tmp(_get_conflict_copy_path(full_path))

    elif c.content_status == CONTENT_STATUS_TO_DIR:
      if not os.path.exists(full_path):
        os.mkdir(full_path)
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                 force_conflict=force_conflict)
      elif os.path.isdir(full_path):
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                 force_conflict=force_conflict)
      else:
        # full_path is still a file
        if c.old_info.is_modified(file_info.load_file_info(full_path)):
          # Conflict, the existing file is changed
          os.rename(full_path, _get_conflict_copy_path(full_path))
        else:
          os.remove(full_path)
        os.mkdir(full_path)
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                 force_conflict=force_conflict)

    elif ((not c.cur_info or not c.cur_info.is_dir)
        and (not c.old_info or not c.old_info.is_dir)):
      # File change
      if c.content_status in [CONTENT_STATUS_NEW,
                              CONTENT_STATUS_MODIFIED]:
        conflict_state = _get_file_conflict_state(c, full_path, force_conflict)
        if conflict_state == CONFLICT_NO_CONFLICT:
          c.cur_info.copy_tmp(full_path)
        elif conflict_state == CONFLICT_NEW:
          c.cur_info.copy_tmp(_get_conflict_copy_path(full_path))
        elif conflict_state == CONFLICT_DEST:
          shutil.move(full_path, _get_conflict_copy_path(full_path))
          c.cur_info.copy_tmp(full_path)
      elif c.content_status == CONTENT_STATUS_DELETED:
        conflict_state = _get_file_conflict_state(c, full_path, force_conflict)
        if conflict_state == CONFLICT_NO_CONFLICT:
          if os.path.exists(full_path):
            os.remove(full_path)

    else:
      # Dir change
      if c.content_status in [CONTENT_STATUS_NEW,
                              CONTENT_STATUS_MODIFIED]:
        conflict_state = _get_dir_conflict_state(c, full_path)
        if conflict_state == CONFLICT_NO_CONFLICT:
          if not os.path.exists(full_path):
            os.mkdir(full_path)
        elif conflict_state == CONFLICT_DEST:
          shutil.move(full_path, _get_conflict_copy_path(full_path))
          os.mkdir(full_path)
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                force_conflict=force_conflict)
      elif c.content_status == CONTENT_STATUS_DELETED:
        conflict_state = _get_dir_conflict_state(c, full_path)
        if conflict_state == CONFLICT_NO_CONFLICT:
          apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                   force_conflict=force_conflict)
          if os.path.isdir(full_path) and not os.listdir(full_path):
            os.rmdir(full_path)
      else:
        # No change
        apply_dir_changes_to_dir(dest_dir, c.dir_changes,
                                 force_conflict=force_conflict)


