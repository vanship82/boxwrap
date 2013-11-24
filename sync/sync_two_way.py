import collections
import copy
import os
import random
import shutil

from sync import change_entry
from sync import file_info
from sync import sync_one_way
from util import util

def sync(dir1, dir_info1, dir2, dir_info2, tmp_dir):
  sync_change_od1 = sync_one_way.get_sync_change_od(dir1, dir_info1, tmp_dir)
  sync_change_od2 = sync_one_way.get_sync_change_od(dir2, dir_info2, tmp_dir)

  new_sc_od1, new_sc_od2 = merge(sync_change_od1, sync_change_od2)
  apply_sync_change_to_dir(sync_changes1_merge)
  apply_sync_change_to_dir(sync_changes2_merge)


def merge(sync_change_od1, sync_change_od2):
  new_od1 = collections.OrderedDict()
  new_od2 = collections.OrderedDict()
  for sc1, sc2 in util.merge_two_iterators(
      sync_change_od1.itervalues(),
      sync_change_od2.itervalues(),
      key_func=lambda x: util.path_for_sorting(x.change.path)):
    if sc1 and sc2:
      if (sc1.change.content_status == change_entry.CONTENT_STATUS_NO_CHANGE
          and
          sc2.change.content_status == change_entry.CONTENT_STATUS_NO_CHANGE):
        new_od1[sc1.change.path] = sc1
        new_od2[sc2.change.path] = sc2

    elif sc1 and not sc2:
      if sc1.change.content_status != change_entry.CONTENT_STATUS_DELETED:
        change = change_entry.ChangeEntry(
            sc1.change.path, sc1.change.cur_info, None,
            change_entry.CONTENT_STATUS_NEW)
        sc = sync_one_way.SyncChangeEntry(change, sc1.tmp_file)
        new_od2[sc1.change.path] = sc

      new_od1[sc1.change.path] = sc1
    elif not sc1 and sc2:
      if sc2.change.content_status != change_entry.CONTENT_STATUS_DELETED:
        change = change_entry.ChangeEntry(
            sc2.change.path, sc2.change.cur_info, None,
            change_entry.CONTENT_STATUS_NEW)
        sc = sync_one_way.SyncChangeEntry(change, sc1.tmp_file)
        new_od1[sc2.change.path] = sc

      new_od2[sc2.change.path] = sc2
    else:
      pass

  return new_od1, new_od2

