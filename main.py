import copy
import os
import shutil
import sys
import time

import compression
from sync import change_entry
from sync import file_info
from sync import merge
from util import util


class BoxWrap:

  def __init__(self, working_dir, cloud_dir, tmp_dir, file_info_csv_file,
               reinit=False, password=None,
               encryption_method=compression.ENCRYPTION_AES_256):
    self.working_dir = working_dir
    self.cloud_dir = cloud_dir
    self.tmp_dir = tmp_dir
    self.file_info_csv_file = file_info_csv_file
    self.password = password
    self.encryption_method = encryption_method
    self.compression_key = lambda x: util.path_for_sorting(
        compression.get_original_filename(x.path))

  # TODO: debug only, remove it
  def _print_changes(self, name, dir_changes):
    print name
    for x in dir_changes.flat_changes():
      print x
      print '    cur_info: %s' % x.cur_info
      print '    old_info: %s' % x.old_info

  # TODO: debug only, remove it
  def _print_di(self, name, dir_info):
    print name
    for x in dir_info.flat_file_info_list():
      print x

  def sync(self, old_dir_info, debug=False):
    tstart = time.time()
    cwd = os.getcwd()
    working_old_di = old_dir_info
    cloud_old_di = self._extract_compressed_dir_info(old_dir_info)
    if debug:
      print '============== step 1: %s' % (time.time() - tstart)

    os.chdir(self.working_dir)
    working_cur_di = file_info.load_dir_info('.', calculate_hash=True)
    working_dc = change_entry.get_dir_changes(working_cur_di, working_old_di,
                                              root_dir=self.working_dir,
                                              tmp_dir=self.tmp_dir)
    working_dc = self._generate_compressed_dir_changes(working_dc)
    if debug:
      self._print_changes('********** working_dc', working_dc)
    if debug:
      print '============== step 2: %s' % (time.time() - tstart)

    os.chdir(self.cloud_dir)
    cloud_cur_di = file_info.load_dir_info(
        '.', calculate_hash=True, key=self.compression_key)
    cloud_dc = change_entry.get_dir_changes(cloud_cur_di, cloud_old_di,
                                            root_dir=self.cloud_dir,
                                            tmp_dir=self.tmp_dir)
    cloud_dc = self._generate_original_dir_changes(cloud_dc)
    if debug:
      self._print_changes('********** cloud_dc', cloud_dc)
    if debug:
      print '============== step 3: %s' % (time.time() - tstart)

    result = merge.merge(working_dc, cloud_dc)

    working_dc_new = result[0]
    working_dc_old = result[1]
    cloud_dc_new = self._extract_compressed_dir_changes(result[2])
    cloud_dc_old = result[3]
    if debug:
      self._print_changes('********** cloud_dc_new', cloud_dc_new)
    if debug:
      print '============== step 4: %s' % (time.time() - tstart)

    change_entry.apply_dir_changes_to_dir(self.working_dir, working_dc_new)
    working_di = change_entry.apply_dir_changes_to_dir_info('.', working_dc_old)
    if debug:
      print '============== step 5: %s' % (time.time() - tstart)
    change_entry.apply_dir_changes_to_dir(self.cloud_dir, cloud_dc_new)
    cloud_di = change_entry.apply_dir_changes_to_dir_info('.', cloud_dc_old)
    if debug:
      print '============== step 6: %s' % (time.time() - tstart)
    os.chdir(cwd)
    return [working_di, cloud_di]

  def _generate_compressed_dir_changes(self, dir_changes):
    dir_changes = copy.deepcopy(dir_changes)
    for c in dir_changes.flat_changes():
      if c.cur_info and c.cur_info.tmp_file:
        compressed_tmp_filename = change_entry.generate_tmp_file(self.tmp_dir)
        compressed_tmp_file = os.path.join(self.tmp_dir,
                                           compressed_tmp_filename)
        compression.compress_file(c.cur_info.tmp_file, compressed_tmp_file,
                                  password=self.password,
                                  encryption_method=self.encryption_method)
        tmp_fi = file_info.load_file_info(compressed_tmp_file)
        compressed_file_info = file_info.FileInfo(
            # TODO: check conflict of compressed filename?
            compression.get_compressed_filename(c.cur_info.path),
            c.cur_info.is_dir, c.cur_info.mode, tmp_fi.size,
            c.cur_info.last_modified_time)
        c.cur_info.compressed_file_info = file_info.copy_with_tmp_file(
            compressed_file_info, compressed_tmp_filename, self.tmp_dir)
    return dir_changes

  def _generate_original_dir_changes(self, dir_changes,
                                     parent_dir_changes=None):
    new_dir_changes = change_entry.DirChanges(
        dir_changes.base_dir(), dir_changes.dir_status(),
        parent_dir_changes=parent_dir_changes)
    for c in dir_changes.changes():
      path = compression.get_original_filename(c.path)
      old_info = None
      if c.old_info and c.old_info.original_file_info:
        old_info = copy.deepcopy(c.old_info.original_file_info)
        old_info.compressed_file_info = copy.deepcopy(c.old_info)
        old_info.compressed_file_info.original_file_info = None
      else:
        old_info = copy.deepcopy(c.old_info)

      cur_info = None
      if c.cur_info:
        if c.cur_info.tmp_file:
          original_tmp_filename = change_entry.generate_tmp_file(self.tmp_dir)
          original_tmp_file = os.path.join(self.tmp_dir,
                                           original_tmp_filename)
          compression.decompress_file(c.cur_info.tmp_file, original_tmp_file,
                                      password=self.password)
          tmp_fi = file_info.load_file_info(original_tmp_file)
          compressed_file_info = copy.deepcopy(c.cur_info)
          compressed_file_info.tmp_file = None
          compressed_file_info.compressed_file_info = None
          compressed_file_info.original_file_info = None
          cur_info = file_info.FileInfo(
              # TODO: check conflict of original filename?
              compression.get_original_filename(c.cur_info.path),
              c.cur_info.is_dir, c.cur_info.mode, tmp_fi.size,
              c.cur_info.last_modified_time,
              compressed_file_info=compressed_file_info)
          cur_info = file_info.copy_with_tmp_file(
              cur_info, original_tmp_filename, self.tmp_dir)
        else:
          cur_info = old_info

      new_dir_changes.add_change(change_entry.ChangeEntry(
        path, cur_info, old_info, c.content_status,
        dir_changes=(self._generate_original_dir_changes(
            c.dir_changes, parent_dir_changes=new_dir_changes)
            if c.dir_changes else None),
        parent_dir_changes=new_dir_changes))

    return new_dir_changes

  def _extract_compressed_dir_changes(self, dir_changes,
                                      parent_dir_changes=None):
    new_dir_changes = change_entry.DirChanges(
        dir_changes.base_dir(), dir_changes.dir_status(),
        parent_dir_changes=parent_dir_changes)
    for c in dir_changes.changes():
      old_info = None
      if c.old_info and c.old_info.compressed_file_info:
        old_info = copy.deepcopy(c.old_info.compressed_file_info)
      else:
        old_info = copy.deepcopy(c.old_info)

      cur_info = None
      if c.cur_info and c.cur_info.compressed_file_info:
        cur_info = copy.deepcopy(c.cur_info.compressed_file_info)
      else:
        cur_info = copy.deepcopy(c.cur_info)
      path = cur_info.path if cur_info else old_info.path

      new_dir_changes.add_change(change_entry.ChangeEntry(
        path, cur_info, old_info, c.content_status,
        dir_changes=(self._extract_compressed_dir_changes(
            c.dir_changes, parent_dir_changes=new_dir_changes)
            if c.dir_changes else None),
        parent_dir_changes=new_dir_changes))

    return new_dir_changes

  def _extract_compressed_dir_info(self, dir_info):
    file_info_list = []
    for fi in dir_info.flat_file_info_list():
      fi2 = copy.deepcopy(fi)
      if fi2.compressed_file_info:
        fi3 = fi2.compressed_file_info
        fi3.original_file_info = fi2
        fi2.compressed_file_info = None
        file_info_list.append(fi3)
      else:
        file_info_list.append(fi2)
    return file_info.load_dir_info_from_file_info_list(
        '.', file_info_list, key=self.compression_key)

