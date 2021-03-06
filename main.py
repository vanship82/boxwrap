import copy
import getpass
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
               compression_level=compression.COMPRESSION_LEVEL_NORMAL,
               encryption_method=compression.ENCRYPTION_ZIP_CRYPTO):
    self.working_dir = working_dir
    self.cloud_dir = cloud_dir
    self.tmp_dir = tmp_dir
    self.file_info_csv_file = file_info_csv_file
    self.password = password
    self.encryption_method = encryption_method
    self.compression_level = compression_level
    self.compression_key = lambda x: util.path_for_sorting(
        compression.get_original_filename(x.path))

  # TODO: debug only, remove it
  def _print_changes(self, name, dir_changes):
    print name
    for x in dir_changes.flat_changes():
      print x
      # print '    cur_info: %s' % x.cur_info
      # print '    old_info: %s' % x.old_info
      # print '    conflict_info: %s' % x.conflict_info

  # TODO: debug only, remove it
  def _print_di(self, name, dir_info):
    print name
    for x in dir_info.flat_file_info_list():
      print x

  def _is_no_change(self, dir_changes):
    for c in dir_changes.flat_changes():
      if c.content_status != change_entry.CONTENT_STATUS_NO_CHANGE:
        return False
    return True

  def sync(self, old_dir_info, debug=False, verbose=False):
    tstart = time.time()
    cwd = os.getcwd()
    working_old_di = old_dir_info
    cloud_old_di = self._extract_compressed_dir_info(old_dir_info)
    if debug:
      print '============== Latency till extract input dir info : %s s' % (
          time.time() - tstart)

    if verbose:
      phase = 1
      print 'Phase %s: Examine changes on working_dir at %s' % (
          phase, self.working_dir)
    os.chdir(self.working_dir)
    working_cur_di = file_info.load_dir_info('.', calculate_hash=True)
    working_dc = change_entry.get_dir_changes(working_cur_di, working_old_di,
                                              root_dir=self.working_dir,
                                              tmp_dir=self.tmp_dir,
                                              verbose=verbose)
    is_working_no_change = self._is_no_change(working_dc)
    working_dc = self._generate_compressed_dir_changes(working_dc)
    if debug:
      print '============== Latency after examing working_dir: %s s' % (
         time.time() - tstart)
      self._print_changes('********** working_dc', working_dc)

    if verbose:
      phase += 1
      print 'Phase %s: Examine changes on wrap_dir at %s' % (
          phase, self.cloud_dir)
    os.chdir(self.cloud_dir)
    cloud_cur_di = file_info.load_dir_info(
        '.', calculate_hash=True, key=self.compression_key)
    cloud_dc = change_entry.get_dir_changes(cloud_cur_di, cloud_old_di,
                                            root_dir=self.cloud_dir,
                                            tmp_dir=self.tmp_dir,
                                            verbose=verbose)
    is_cloud_no_change = self._is_no_change(cloud_dc)
    cloud_dc_result = self._generate_original_dir_changes(cloud_dc)
    cloud_dc = cloud_dc_result[0]
    invalid_archives_dc_working = cloud_dc_result[1]
    invalid_archives_dc_cloud = cloud_dc_result[2]
    if invalid_archives_dc_working:
      if debug:
        self._print_changes('************ invalid_archives_dc',
                            invalid_archives_dc_working)
      # Apply invalid_archives_dc to working dir because they are not
      # compressed. These files will be compressed and sync after next sync.
      change_entry.apply_dir_changes_to_dir(self.working_dir,
                                            invalid_archives_dc_working,
                                            verbose=verbose)
      change_entry.apply_dir_changes_to_dir(self.cloud_dir,
                                            invalid_archives_dc_cloud,
                                            verbose=verbose)
    if debug:
      print '============== Latency after examing wrap_dir: %s s' % (
          time.time() - tstart)
    has_changes = not is_working_no_change or not is_cloud_no_change

    if has_changes and verbose:
      phase += 1
      print 'Phase %s: Merge changes on both dirs' % phase
    result = merge.merge(working_dc, cloud_dc)

    working_dc_new = result[0]
    working_dc_old = result[1]
    cloud_dc_new = self._extract_compressed_dir_changes(result[2])
    cloud_dc_old = result[3]
    working_dc_conflict = result[4]
    cloud_dc_conflict = self._extract_compressed_dir_changes(
        working_dc_conflict)
    if debug:
      print '============== Latency after merge: %s s' % (time.time() - tstart)
      self._print_changes('********** working_dc_conflict', working_dc_conflict)
      self._print_changes('********** cloud_dc_conflict', cloud_dc_conflict)

    if has_changes and verbose:
      phase += 1
      print 'Phase %s: Apply merged changes on working_dir at %s' % (
          phase, self.working_dir)
    change_entry.apply_dir_changes_to_dir(self.working_dir, working_dc_new,
                                          verbose=verbose)
    change_entry.apply_dir_changes_to_dir(
        self.working_dir, working_dc_conflict,
        force_conflict=change_entry.CONFLICT_NEW,
        verbose=verbose)
    working_di = change_entry.apply_dir_changes_to_dir_info('.', working_dc_old)
    if debug:
      print '============== Latency after applying merged changes on working_dir: %s' % (time.time() - tstart)

    if has_changes and verbose:
      phase += 1
      print 'Phase %s: Apply merged changes on wrap_dir at %s' % (
          phase, self.cloud_dir)
    change_entry.apply_dir_changes_to_dir(self.cloud_dir, cloud_dc_new,
                                          verbose=verbose)
    change_entry.apply_dir_changes_to_dir(
        self.cloud_dir, cloud_dc_conflict,
        force_conflict=change_entry.CONFLICT_NEW,
        verbose=verbose)
    cloud_di = change_entry.apply_dir_changes_to_dir_info('.', cloud_dc_old)
    if debug:
      print '============== Latency after applying merged changes on wrap_dir: %s' % (time.time() - tstart)

    os.chdir(cwd)
    return [has_changes, working_di, cloud_di]

  def _generate_compressed_dir_changes(self, dir_changes):
    dir_changes = copy.deepcopy(dir_changes)
    for c in dir_changes.flat_changes():
      if c.cur_info and c.cur_info.tmp_file:
        compressed_tmp_filename = change_entry.generate_tmp_file(self.tmp_dir)
        compressed_tmp_file = os.path.join(self.tmp_dir,
                                           compressed_tmp_filename)
        tmp_file_with_realname = os.path.join(self.tmp_dir,
                                              os.path.basename(c.path))
        # Rename the tmp file so that the archive includes the original
        # filename.
        os.rename(c.cur_info.tmp_file, tmp_file_with_realname)
        compression.compress_file(tmp_file_with_realname, compressed_tmp_file,
                                  password=self.password,
                                  encryption_method=self.encryption_method,
                                  compression_level=self.compression_level)
        # Rename the tmp filename back.
        os.rename(tmp_file_with_realname, c.cur_info.tmp_file)
        tmp_fi = file_info.load_file_info(compressed_tmp_file)
        compressed_file_info = file_info.FileInfo(
            # TODO: check conflict of compressed filename?
            compression.get_compressed_filename(c.cur_info.path),
            c.cur_info.is_dir, c.cur_info.mode, tmp_fi.size,
            c.cur_info.last_modified_time)
        c.cur_info.compressed_file_info = file_info.copy_with_tmp_file(
            compressed_file_info, compressed_tmp_filename, self.tmp_dir)
    return dir_changes

  # Return (dir_changes, invalid_archive_dc_working, invalid_archive_dc_cloud)
  def _generate_original_dir_changes(self, dir_changes,
                                     parent_dir_changes=None,
                                     parent_invalid_archive_dc_working=None,
                                     parent_invalid_archive_dc_cloud=None):
    invalid_archive_dc_working = change_entry.DirChanges(
        dir_changes.base_dir(),
        change_entry.CONTENT_STATUS_MODIFIED,
        parent_dir_changes=parent_invalid_archive_dc_working)
    invalid_archive_dc_cloud = change_entry.DirChanges(
        dir_changes.base_dir(),
        change_entry.CONTENT_STATUS_MODIFIED,
        parent_dir_changes=parent_invalid_archive_dc_cloud)
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
        if c.cur_info.is_dir:
          cur_info = c.cur_info
        elif c.cur_info.tmp_file:
          original_tmp_filename = change_entry.generate_tmp_file(self.tmp_dir)
          original_tmp_file = os.path.join(self.tmp_dir,
                                           original_tmp_filename)
          if not compression.is_compressed_filename(c.cur_info.path):
            invalid_archive_dc_working.add_change(change_entry.ChangeEntry(
                path, c.cur_info, c.old_info, c.content_status,
                parent_dir_changes=invalid_archive_dc_working))
            invalid_archive_dc_cloud.add_change(change_entry.ChangeEntry(
                path, None, c.cur_info,
                # Remove the file directly because we move it to working dir
                change_entry.CONTENT_STATUS_DELETED,
                parent_dir_changes=invalid_archive_dc_cloud))
            continue
          try:
            compression.decompress_file(c.cur_info.tmp_file, original_tmp_file,
                                        self.tmp_dir, password=self.password)
          except compression.CompressionInvalidArchive:
            invalid_archive_dc_working.add_change(change_entry.ChangeEntry(
                # Not using path because it is not a valid archive
                c.path, c.cur_info, c.old_info, c.content_status,
                parent_dir_changes=invalid_archive_dc_working))
            invalid_archive_dc_cloud.add_change(change_entry.ChangeEntry(
                # Not using path because it is not a valid archive
                c.path, None, c.cur_info,
                # Remove the file directly because we move it to working dir
                change_entry.CONTENT_STATUS_DELETED,
                parent_dir_changes=invalid_archive_dc_cloud))
            continue

          tmp_fi = file_info.load_file_info(original_tmp_file)
          compressed_file_info = copy.deepcopy(c.cur_info)
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

      sub_dir_changes = None
      sub_invalid_archive_dc_working = None
      if c.dir_changes:
        result = self._generate_original_dir_changes(
                c.dir_changes,
                parent_dir_changes=new_dir_changes,
                parent_invalid_archive_dc_working=invalid_archive_dc_working)
        sub_dir_changes = result[0]
        sub_invalid_archive_dc_working = result[1]
        sub_invalid_archive_dc_cloud = result[2]
        if sub_invalid_archive_dc_working:
          invalid_archive_dc_working.add_change(change_entry.ChangeEntry(
              path, cur_info, old_info, c.content_status,
              dir_changes=sub_invalid_archive_dc_working,
              parent_dir_changes=invalid_archive_dc_working))
        if sub_invalid_archive_dc_cloud:
          invalid_archive_dc_cloud.add_change(change_entry.ChangeEntry(
              path, cur_info, old_info, c.content_status,
              dir_changes=sub_invalid_archive_dc_cloud,
              parent_dir_changes=invalid_archive_dc_cloud))
      new_dir_changes.add_change(change_entry.ChangeEntry(
          path, cur_info, old_info, c.content_status,
          dir_changes=sub_dir_changes,
          parent_dir_changes=new_dir_changes))

    if not invalid_archive_dc_working.changes():
      invalid_archive_dc_working = None
    if not invalid_archive_dc_cloud.changes():
      invalid_archive_dc_cloud = None
    return new_dir_changes, invalid_archive_dc_working, invalid_archive_dc_cloud

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

      conflict_info = None
      if c.conflict_info and c.conflict_info.compressed_file_info:
        conflict_info = copy.deepcopy(c.conflict_info.compressed_file_info)
      else:
        conflict_info = copy.deepcopy(c.conflict_info)

      path = cur_info.path if cur_info else old_info.path

      new_dir_changes.add_change(change_entry.ChangeEntry(
        path, cur_info, old_info, c.content_status,
        dir_changes=(self._extract_compressed_dir_changes(
            c.dir_changes, parent_dir_changes=new_dir_changes)
            if c.dir_changes else None),
        parent_dir_changes=new_dir_changes,
        conflict_info=conflict_info))

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

