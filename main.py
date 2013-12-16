import copy
import os
import shutil
import sys

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

  def sync(self, old_dir_info):
    cwd = os.getcwd()
    working_old_di = old_dir_info
    cloud_old_di = self._extract_compressed_dir_info(old_dir_info)

    os.chdir(self.working_dir)
    working_cur_di = file_info.load_dir_info('.', calculate_hash=True)
    working_dc = change_entry.get_dir_changes(working_cur_di, working_old_di,
                                              root_dir=self.working_dir,
                                              tmp_dir=self.tmp_dir)
    working_dc = self._generate_compressed_dir_changes(working_dc)

    os.chdir(self.cloud_dir)
    cloud_cur_di = file_info.load_dir_info(
        '.', calculate_hash=True, key=self.compression_key)
    cloud_dc = change_entry.get_dir_changes(cloud_cur_di, cloud_old_di,
                                            root_dir=self.cloud_dir,
                                            tmp_dir=self.tmp_dir)
    cloud_dc = self._generate_original_dir_changes(cloud_dc)

    result = merge.merge(working_dc, cloud_dc)

    working_dc_new = result[0]
    working_dc_old = result[1]
    cloud_dc_new = self._flip_compressed_dir_changes(result[2])
    cloud_dc_old = result[3]

    change_entry.apply_dir_changes_to_dir(self.working_dir, working_dc_new)
    working_di = change_entry.apply_dir_changes_to_dir_info('.', working_dc_old)
    change_entry.apply_dir_changes_to_dir(self.cloud_dir, cloud_dc_new)
    cloud_di = change_entry.apply_dir_changes_to_dir_info('.', cloud_dc_old)
    os.chdir(cwd)
    return [working_di, cloud_di]

  def _flip_compressed_dir_changes(self, dir_changes):
    dir_changes = copy.deepcopy(dir_changes)
    for c in dir_changes.flat_changes():
      if c.cur_info and c.cur_info.compressed_file_info:
        c.path = c.cur_info.compressed_file_info.path
        c.cur_info.copy(c.cur_info.compressed_file_info)
    return dir_changes

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

  # TODO: implement this
  def _generate_original_dir_changes(self, dir_changes):
    dir_changes = copy.deepcopy(dir_changes)
    return dir_changes

  def _extract_compressed_dir_info(self, dir_info):
    file_info_list = []
    for fi in dir_info.flat_file_info_list():
      fi2 = copy.deepcopy(fi)
      if fi2.compressed_file_info:
        file_info_list.append(fi2.compressed_file_info)
      else:
        file_info_list.append(fi2)
    return file_info.load_dir_info_from_file_info_list(
        '.', file_info_list, key=self.compression_key)

