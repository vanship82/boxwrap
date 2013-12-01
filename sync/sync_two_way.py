import collections
import copy
import os
import random
import shutil

from sync import change_entry
from sync import file_info
from sync import sync_one_way
from util import util


class SyncTwoWayChangeEntry:
  """ Two way change with conflict resolution.
  """

  def __init__(self, sync_change, conflict_sync_change=None):
    self.sync_change = sync_change
    self.conflict_sync_change = conflict_sync_change


def sync(dir1, dir_info1, dir2, dir_info2, tmp_dir):
  sync_change_od1 = sync_one_way.get_sync_change_od(dir1, dir_info1, tmp_dir)
  sync_change_od2 = sync_one_way.get_sync_change_od(dir2, dir_info2, tmp_dir)

  new_sc_od1, new_sc_od2 = merge(sync_change_od1, sync_change_od2)
  apply_sync_change_to_dir(sync_changes1_merge)
  apply_sync_change_to_dir(sync_changes2_merge)


def _sync_change(change, dc_new, dc_old, change_on_dc_new=True,
                 dir_changes_new=None, dir_changes_old=None):
  cur_info = copy.deepcopy(change.cur_info) if change.cur_info else None
  old_info = copy.deepcopy(change.old_info) if change.old_info else None
  dc_old.add_change(
      change_entry.ChangeEntry(
          change.path, cur_info, old_info, change.content_status,
          dir_changes=dir_changes_old, parent_dir_changes=dc_old))
  if change_on_dc_new:
    dc_new.add_change(
        change_entry.ChangeEntry(
            change.path, cur_info, old_info, change.content_status,
            dir_changes=dir_changes_new, parent_dir_changes=dc_new))
  elif change.content_status != change_entry.CONTENT_STATUS_DELETED:
    dc_new.add_change(
        change_entry.ChangeEntry(
            change.path, change.cur_info, change.cur_info,
            change_entry.CONTENT_STATUS_NO_CHANGE,
            dir_changes=dir_changes_new, parent_dir_changes=dc_new))


def _merge_both_files(c1, c2, dc_new1, dc_old1, dc_new2, dc_old2,
                      changes_conflict):
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
      # TODO: conflict
      pass
    else:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
  elif c1.content_status == change_entry.CONTENT_STATUS_NEW:
    if c2 and c2.content_status == change_entry.CONTENT_STATUS_NEW:
      # TODO: conflict
      pass
    else:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
  elif c1.content_status == change_entry.CONTENT_STATUS_DELETED:
    if c2.content_status == change_entry.CONTENT_STATUS_DELETED:
      # no sync
      _sync_change(c1, dc_new1, dc_old1)
      _sync_change(c2, dc_new2, dc_old2)
    elif c2.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
      # sync c1 to c2
      _sync_change(c1, dc_new1, dc_old1, change_on_dc_new=False)
      _sync_change(c1, dc_new2, dc_old2)
    elif c2.content_status == change_entry.CONTENT_STATUS_FILE_MODIFIED:
      # sync c2 to c1
      _sync_change(c2, dc_new1, dc_old1)
      _sync_change(c2, dc_new2, dc_old2, change_on_dc_new=False)


def _merge_both_dirs(c1, c2, dc1, dc2,
                     dc_new1, dc_old1, dc_new2, dc_old2, changes_conflict):
  if not c1:
    if not c2 and c2.content_status == change_entry.CONTENT_STATUS_NEW:
      _sync_change(c2, dc_new1, dc_old1)
  elif c1.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
    if c2.content_status == change_entry.CONTENT_STATUS_NO_CHANGE:
      # no change
      results = merge(dc1, dc2,
                      parent_dir_changes_new1=dc_new1,
                      parent_dir_changes_old1=dc_old1,
                      parent_dir_changes_new2=dc_new2,
                      parent_dir_changes_old2=dc_old2,
                      changes_conflict=changes_conflict)
      _sync_change(c1, dc_new1, dc_old1, dir_changes_new=results[0],
                   dir_changes_old=results[1])
      _sync_change(c2, dc_new2, dc_old2, dir_changes_new=results[2],
                   dir_changes_old=results[3])


def _is_file_change(change):
  if not change:
    return True
  if change.cur_info and change.old_info:
    return not change.cur_info.is_dir and not change.old_info.is_dir
  elif change.cur_info:
    return not change.cur_info.is_dir
  else:
    return not change.old_info.is_dir


# Conflict resolution favorite dir_changes1.
# Returns: a tuple of
#   dir_changes_new1, the dir_changes with merge for the new dir1.
#   dir_changes_old1, the dir_changes with merge for the old dir1.
#   dir_changes_new2, the dir_changes with merge for the new dir2.
#   dir_changes_old2, the dir_changes with merge for the old dir2.
#   changes_conflict, the list of changes for conflicts, maybe changed.
def merge(dir_changes1, dir_changes2,
          parent_dir_changes_new1=None,
          parent_dir_changes_old1=None,
          parent_dir_changes_new2=None,
          parent_dir_changes_old2=None,
          changes_conflict=None):
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
  if not changes_conflict:
    changes_conflict = []
  for c1, c2 in util.merge_two_iterators(
      iter(dir_changes1.changes() if dir_changes1 else []),
      iter(dir_changes2.changes() if dir_changes2 else []),
      key_func=lambda x: util.path_for_sorting(x.path)):
    if _is_file_change(c1) and _is_file_change(c2):
      _merge_both_files(c1, c2, dc_new1, dc_old1, dc_new2, dc_old2,
                        changes_conflict)
    elif not _is_file_change(c1) and not _is_file_change(c2):
      _merge_both_dirs(c1, c2,
                       dir_changes1.dir_changes(c1.path),
                       dir_changes2.dir_changes(c2.path),
                       dc_new1, dc_old1, dc_new2, dc_old2,
                       changes_conflict)

  return dc_new1, dc_old1, dc_new2, dc_old2, changes_conflict

