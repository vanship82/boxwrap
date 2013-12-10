import collections
import copy
import os
import random
import shutil

from sync import change_entry
from sync import file_info
from util import util


class SyncTwoWayChangeEntry:
  """ Two way change with conflict resolution.
  """

  def __init__(self, sync_change, conflict_sync_change=None):
    self.sync_change = sync_change
    self.conflict_sync_change = conflict_sync_change


def _sync_conflict(change, dc_conflict, dir_changes=None):
  cur_info = copy.deepcopy(change.cur_info) if change.cur_info else None
  dc_conflict.add_change(
      change_entry.ChangeEntry(
          change.path, cur_info, None, change_entry.CONTENT_STATUS_NO_CHANGE,
          dir_changes=dir_changes, parent_dir_changes=dc_conflict))


def _sync_change(change, dc_new, dc_old, change_on_dc_new=True,
                 dir_changes_new=None, dir_changes_old=None,
                 content_status_new=change_entry.CONTENT_STATUS_UNSPECIFIED,
                 content_status_old=change_entry.CONTENT_STATUS_UNSPECIFIED):
  cur_info = copy.deepcopy(change.cur_info) if change.cur_info else None
  old_info = copy.deepcopy(change.old_info) if change.old_info else None
  if content_status_new == change_entry.CONTENT_STATUS_UNSPECIFIED:
    content_status_new = change.content_status
    if dir_changes_new and dir_changes_new.changes():
      if dir_changes_new.dir_status() == change_entry.CONTENT_STATUS_NO_CHANGE:
        content_status_new = change_entry.CONTENT_STATUS_NO_CHANGE
      elif (content_status_new == change_entry.CONTENT_STATUS_DELETED
          and dir_changes_new.dir_status() !=
              change_entry.CONTENT_STATUS_DELETED):
        # Need recover cur_info
        cur_info = copy.deepcopy(change.old_info) if change.old_info else None
        content_status_new = change_entry.CONTENT_STATUS_MODIFIED
      elif content_status_new == change_entry.CONTENT_STATUS_NEW:
        content_status_new = dir_changes_new.dir_status()
  if content_status_old == change_entry.CONTENT_STATUS_UNSPECIFIED:
    content_status_old = change.content_status
    if dir_changes_old and dir_changes_old.changes():
      if dir_changes_old.dir_status() == change_entry.CONTENT_STATUS_NO_CHANGE:
        content_status_old = change_entry.CONTENT_STATUS_NO_CHANGE
      elif (content_status_old == change_entry.CONTENT_STATUS_DELETED
          and dir_changes_old.dir_status() !=
              change_entry.CONTENT_STATUS_DELETED):
        # Need recover cur_info
        cur_info = copy.deepcopy(change.old_info) if change.old_info else None
        content_status_old = change_entry.CONTENT_STATUS_MODIFIED
      elif content_status_old == change_entry.CONTENT_STATUS_NEW:
        content_status_old = dir_changes_old.dir_status()
  dc_old.add_change(
      change_entry.ChangeEntry(
          change.path, cur_info, old_info, content_status_old,
          dir_changes=dir_changes_old, parent_dir_changes=dc_old))
  if change_on_dc_new:
    dc_new.add_change(
        change_entry.ChangeEntry(
            change.path, cur_info, old_info, content_status_new,
            dir_changes=dir_changes_new, parent_dir_changes=dc_new))
  elif change.content_status != change_entry.CONTENT_STATUS_DELETED:
    dc_new.add_change(
        change_entry.ChangeEntry(
            change.path, change.cur_info, change.cur_info,
            change_entry.CONTENT_STATUS_NO_CHANGE,
            dir_changes=dir_changes_new, parent_dir_changes=dc_new))


def _merge_both_files(c1, c2, dc_new1, dc_old1, dc_new2, dc_old2,
                      dc_conflict):
  if not c1:
    if not c2 and c2.content_status == change_entry.CONTENT_STATUS_NEW:
      _sync_change(c2, dc_new1, dc_old1)
    else:
      # sync c2 to c1
      _sync_change(c2, dc_new1, dc_old1)
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False)
  elif c1.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
    if c2.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
      # no change
      _sync_change(c1, dc_new1, dc_old1)
      _sync_change(c2, dc_new2, dc_old2)
    else:
      # sync c2 to c1
      _sync_change(c2, dc_new1, dc_old1)
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False)
  elif c1.content_status == change_entry.CONTENT_STATUS_MODIFIED:
    if c2.content_status == change_entry.CONTENT_STATUS_MODIFIED:
      # conflict, sync c1 to c2 and put c2 into conflict
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
      dc_conflict.add_change(c2)
    elif c2.content_status == change_entry.CONTENT_STATUS_DELETED:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False,
                   content_status_new=change_entry.CONTENT_STATUS_NO_CHANGE)
      _sync_change(c1, dc_new2, dc_old2,
                   content_status_new=change_entry.CONTENT_STATUS_NEW)
    else:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
  elif c1.content_status == change_entry.CONTENT_STATUS_NEW:
    if c2 and c2.content_status == change_entry.CONTENT_STATUS_NEW:
      if c1.cur_info.is_modified(c2.cur_info, force_check_content=True):
        _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
        _sync_change(c1, dc_new2, dc_old2,
                     content_status_new=change_entry.CONTENT_STATUS_MODIFIED)
        dc_conflict.add_change(c2)
      else:
        # New files are identical, no sync
        _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
        _sync_change(c1, dc_new2, dc_old2, change_on_dc_new=False)
    else:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
  elif c1.content_status == change_entry.CONTENT_STATUS_DELETED:
    if c2.content_status == change_entry.CONTENT_STATUS_DELETED:
      # no sync
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False)
    elif c2.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
    elif c2.content_status == change_entry.CONTENT_STATUS_MODIFIED:
      # sync c2 to c1
      _sync_change(c2, dc_new1, dc_old1,
                   content_status_new=change_entry.CONTENT_STATUS_NEW)
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False)


def _merge_both_dirs(c1, c2, dc1, dc2,
                     dc_new1, dc_old1, dc_new2, dc_old2, dc_conflict):
  results = merge(dc1, dc2,
                  parent_dir_changes_new1=dc_new1,
                  parent_dir_changes_old1=dc_old1,
                  parent_dir_changes_new2=dc_new2,
                  parent_dir_changes_old2=dc_old2,
                  parent_dir_changes_conflict=dc_conflict)
  if not c1:
    if not c2 and c2.content_status == change_entry.CONTENT_STATUS_NEW:
      _sync_change(c2, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
  elif c1.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
    if c2.content_status == change_entry.CONTENT_STATUS_DELETED:
      # sync c2 to c1
      _sync_change(c2, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False,
                   dir_changes_new=results[2], dir_changes_old=results[3])
    else:
      # no sync, maybe conflict
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
      if results[4].changes():
        _sync_conflict(c1, dc_conflict, results[4])
  elif c1.content_status == change_entry.CONTENT_STATUS_MODIFIED:
    # no sync, maybe conflict
    _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                 dir_changes_old=results[1])
    _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                 dir_changes_old=results[3])
    if results[4].changes():
      _sync_conflict(c1, dc_conflict, results[4])
  elif c1.content_status == change_entry.CONTENT_STATUS_NEW:
    if not c2:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c1, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
    else:
      # no sync, maybe conflict
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
      if results[4].changes():
        _sync_conflict(c1, dc_conflict, results[4])
  elif c1.content_status == change_entry.CONTENT_STATUS_DELETED:
    if c2.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False,
                   dir_changes_new=results[0], dir_changes_old=results[1])
      _sync_change(c1, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
    elif c2.content_status == change_entry.CONTENT_STATUS_DELETED:
      # no sync
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False,
                   dir_changes_new=results[0], dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False,
                   dir_changes_new=results[2], dir_changes_old=results[3])
    else:
      # no sync, maybe conflict
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
      if results[4].changes():
        _sync_conflict(c1, dc_conflict, results[4])


def _merge_file_dir(c1, c2, dc1, dc2,
                    dc_new1, dc_old1, dc_new2, dc_old2, dc_conflict):
  if c1.content_status == change_entry.CONTENT_STATUS_TO_FILE:
    results = merge(dc1, dc2,
                    parent_dir_changes_new1=dc_new1,
                    parent_dir_changes_old1=dc_old1,
                    parent_dir_changes_new2=dc_new2,
                    parent_dir_changes_old2=dc_old2,
                    parent_dir_changes_conflict=dc_conflict)
    if c2.content_status in [change_entry.CONTENT_STATUS_NO_CHANGE,
                             change_entry.CONTENT_STATUS_DELETED,
                             change_entry.CONTENT_STATUS_TO_FILE]:
      # sync c1 to c2, maybe conflict
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False,
                   dir_changes_new=result[0], dir_changes_old=result[1])
      _sync_change(c1, dc_new2, dc_old2,
                   dir_changes_new=result[2], dir_changes_old=result[3])
    else:
      # TODO: conflict, treat c1 as DELETED and make c1 cur_info to be a
      # conflict no change to existing dir
      pass
  elif c1.content_status == change_entry.CONTENT_STATUS_TO_DIR:
    if c2.content_status == change_entry.CONTENT_STATUS_TO_DIR:
      results = merge(dc1, dc2,
                      parent_dir_changes_new1=dc_new1,
                      parent_dir_changes_old1=dc_old1,
                      parent_dir_changes_new2=dc_new2,
                      parent_dir_changes_old2=dc_old2,
                      parent_dir_changes_conflict=dc_conflict)
      # no sync, maybe conflict
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])
      if results[4].changes():
        _sync_conflict(c1, dc_conflict, results[4])
    else:
      # TODO: conflict, treat c2 as DELETED and make c1 cur_info to be a
      # conflict no change to existing dir
      pass
  else:
    if c2.content_status == change_entry.CONTENT_STATUS_TO_FILE:
      results = merge(dc1, dc2,
                      parent_dir_changes_new1=dc_new1,
                      parent_dir_changes_old1=dc_old1,
                      parent_dir_changes_new2=dc_new2,
                      parent_dir_changes_old2=dc_old2,
                      parent_dir_changes_conflict=dc_conflict)
      if c1.content_status in [change_entry.CONTENT_STATUS_NO_CHANGE,
                               change_entry.CONTENT_STATUS_DELETED,
                               # Actually, the below status is checked
                               change_entry.CONTENT_STATUS_TO_FILE]:
        # sync c2 to c1, maybe conflict
        _sync_change(c2, dc_new1, dc_old1, change_on_dc_new=False,
                     dir_changes_new=result[0], dir_changes_old=result[1])
        _sync_change(c2, dc_new2, dc_old2,
                     dir_changes_new=result[2], dir_changes_old=result[3])
      else:
        # TODO: conflict, treat c2 as DELETED and make c2 cur_info to be a
        # conflict no change to existing dir
        pass
    elif c1.content_status == change_entry.CONTENT_STATUS_TO_DIR:
      # c2 TO_DIR is already checked
      # TODO: conflict, treat c1 as DELETED and make c1 cur_info to be a
      # conflict no change to existing dir
      pass


def _is_file_change(change):
  if not change:
    return True
  if change.cur_info and change.old_info:
    return not change.cur_info.is_dir and not change.old_info.is_dir
  elif change.cur_info:
    return not change.cur_info.is_dir
  else:
    return not change.old_info.is_dir


def _is_dir_change(change):
  if not change:
    return True
  if change.cur_info and change.old_info:
    return change.cur_info.is_dir and change.old_info.is_dir
  elif change.cur_info:
    return change.cur_info.is_dir
  else:
    return change.old_info.is_dir


# Conflict resolution favorite dir_changes1.
# Returns: a tuple of
#   dir_changes_new1, the dir_changes with merge for the new dir1.
#   dir_changes_old1, the dir_changes with merge for the old dir1.
#   dir_changes_new2, the dir_changes with merge for the new dir2.
#   dir_changes_old2, the dir_changes with merge for the old dir2.
#   dir_changes_conflict, the dir_changes for conflicts.
def merge(dir_changes1, dir_changes2,
          parent_dir_changes_new1=None,
          parent_dir_changes_old1=None,
          parent_dir_changes_new2=None,
          parent_dir_changes_old2=None,
          parent_dir_changes_conflict=None):
  dc_new1 = change_entry.DirChanges(dir_changes1.base_dir(),
                                    change_entry.CONTENT_STATUS_UNSPECIFIED,
                                    parent_dir_changes=parent_dir_changes_new1)
  dc_old1 = change_entry.DirChanges(dir_changes1.base_dir(),
                                    change_entry.CONTENT_STATUS_UNSPECIFIED,
                                    parent_dir_changes=parent_dir_changes_old1)
  dc_new2 = change_entry.DirChanges(dir_changes2.base_dir(),
                                    change_entry.CONTENT_STATUS_UNSPECIFIED,
                                    parent_dir_changes=parent_dir_changes_new2)
  dc_old2 = change_entry.DirChanges(dir_changes2.base_dir(),
                                    change_entry.CONTENT_STATUS_UNSPECIFIED,
                                    parent_dir_changes=parent_dir_changes_old2)
  dc_conflict = change_entry.DirChanges(
      dir_changes1.base_dir(), change_entry.CONTENT_STATUS_UNSPECIFIED,
      parent_dir_changes=parent_dir_changes_conflict)
  for c1, c2 in util.merge_two_iterators(
      iter(dir_changes1.changes() if dir_changes1 else []),
      iter(dir_changes2.changes() if dir_changes2 else []),
      key_func=lambda x: util.path_for_sorting(x.path)):
    if _is_file_change(c1) and _is_file_change(c2):
      _merge_both_files(c1, c2, dc_new1, dc_old1, dc_new2, dc_old2,
                        dc_conflict)
    elif _is_dir_change(c1) and _is_dir_change(c2):
      _merge_both_dirs(c1, c2,
                       dir_changes1.dir_changes(c1.path),
                       dir_changes2.dir_changes(c2.path),
                       dc_new1, dc_old1, dc_new2, dc_old2,
                       dc_conflict)
    else:
      _merge_file_dir(c1, c2,
                      dir_changes1.dir_changes(c1.path),
                      dir_changes2.dir_changes(c2.path),
                      dc_new1, dc_old1, dc_new2, dc_old2,
                      dc_conflict)

  return dc_new1, dc_old1, dc_new2, dc_old2, dc_conflict
