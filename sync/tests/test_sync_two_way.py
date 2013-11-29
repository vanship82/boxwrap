import collections
import inspect
import os
import shutil
import unittest

import cStringIO

from sync import sync_one_way
from sync import sync_two_way
from sync import file_info
from sync import change_entry
from util import util

_TEST_TMP_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_tmp')
_TEST_DIR1 = os.path.join(_TEST_TMP_BASE_DIR, 'dir1')
_TEST_DIR2 = os.path.join(_TEST_TMP_BASE_DIR, 'dir2')
_TEST_TMP = os.path.join(_TEST_TMP_BASE_DIR, 'tmp')
_TEST_CASE_FILE = 'test.txt'
_TEST_CASE_FILE_NEW = 'test_new.txt'
_TEST_CASE_DIR = 'test_dir'
_TEST_CASE_DIR_NEW = 'test_dir_new'

_TEST_INITIAL_CONTENT = 'test'


class TestMergeFile(unittest.TestCase):

  def setUp(self):
    try:
      shutil.rmtree(_TEST_DIR1)
    except:
      pass
    try:
      shutil.rmtree(_TEST_DIR2)
    except:
      pass
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.makedirs(_TEST_DIR1)
    os.makedirs(_TEST_DIR2)
    os.makedirs(_TEST_TMP)

    self.sync_file_info_list1 = self._get_sync_file_info_list(
        _TEST_DIR1, file_info.empty_dir_info(_TEST_DIR1), _TEST_TMP)
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.sync_file_info_list1 = self._get_sync_file_info_list(
        _TEST_DIR1,
        self._get_sync_dir_info(_TEST_DIR1, self.sync_file_info_list1),
        _TEST_TMP)
    self.dir_info1 = self._get_sync_dir_info(_TEST_DIR1,
                                             self.sync_file_info_list1)

    self.sync_file_info_list2 = self._get_sync_file_info_list(
        _TEST_DIR2, file_info.empty_dir_info(_TEST_DIR1), _TEST_TMP)
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.sync_file_info_list2 = self._get_sync_file_info_list(
        _TEST_DIR1,
        self._get_sync_dir_info(_TEST_DIR1, self.sync_file_info_list2),
        _TEST_TMP)
    self.dir_info2 = self._get_sync_dir_info(_TEST_DIR2,
                                             self.sync_file_info_list2)
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.mkdir(_TEST_TMP)

  def _get_sync_file_info_list(self, src_dir_path, dest_dir_info, tmp_dir):
    sync_file_info_list = []
    for path, sync_change in sync_one_way.generate_sync_changes(
        src_dir_path, dest_dir_info, tmp_dir):
      sync_file_info = sync_one_way.apply_sync_change_to_file_info(sync_change)
      if sync_file_info:
        sync_file_info_list.append(sync_file_info)
    return sync_file_info_list

  def _get_sync_dir_info(self, dir_path, sync_file_info_list):
    return file_info.DirInfo(
        dir_path,
        [sync_file_info.file_info for sync_file_info in sync_file_info_list])

  def _get_dir_info_from_sync_change_od(self, dir_path, sync_change_od):
    file_info_list = []
    for sync_two_way_change in sync_change_od.itervalues():
      sync_file_info = sync_one_way.apply_sync_change_to_file_info(sync_change)
      if sync_file_info:
        file_info_list.append(sync_file_info.file_info)
    return file_info.DirInfo(dir_path, file_info_list)

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  def _assertDirInfoEqual(self, dir_info1, dir_info2):
    for fi1, fi2 in util.merge_two_iterators(
        iter(dir_info1.file_info_list()),
        iter(dir_info2.file_info_list()),
        key_func=lambda x: x.path_for_sorting()):
      self.assertIsNotNone(fi1)
      self.assertIsNotNone(fi2)
      self.assertEquals(fi1.path, fi2.path)
      self.assertEquals(fi1.is_dir, fi2.is_dir)
      self.assertFalse(fi1.is_modified(fi2))

  def _merge_for_test(self):
    sync_change_od1 = sync_one_way.get_sync_change_od(
        _TEST_DIR1, self.dir_info1, _TEST_TMP)
    sync_change_od2 = sync_one_way.get_sync_change_od(
        _TEST_DIR2, self.dir_info2, _TEST_TMP)

    new_sc_od1, new_sc_od2 = sync_two_way.merge(sync_change_od1,
                                                sync_change_od2)
    return (new_sc_od1, new_sc_od2,
            self._get_dir_info_from_sync_change_od(_TEST_DIR1, new_sc_od1),
            self._get_dir_info_from_sync_change_od(_TEST_DIR2, new_sc_od2))

  def testInitialSync(self):
    new_sc_od1, new_sc_od2, new_di1, new_di2 = self._merge_for_test()

    self.assertEquals(2, len(new_sc_od1))
    self.assertEquals(change_entry.CONTENT_STATUS_NO_CHANGE,
                      new_sc_od1['.'].change.content_status)
    self.assertEquals(
        change_entry.CONTENT_STATUS_NO_CHANGE,
        new_sc_od1[os.path.join('.', _TEST_CASE_FILE)].change.content_status)
    self.assertEquals(2, len(new_sc_od2))
    self.assertEquals(change_entry.CONTENT_STATUS_NO_CHANGE,
                      new_sc_od2['.'].change.content_status)
    self.assertEquals(
        change_entry.CONTENT_STATUS_NO_CHANGE,
        new_sc_od2[os.path.join('.', _TEST_CASE_FILE)].change.content_status)

    self._assertDirInfoEqual(new_di1, new_di2)

  def testSyncNewFileLeft(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()

    new_sc_od1, new_sc_od2, new_di1, new_di2 = self._merge_for_test()

    self.assertEquals(3, len(new_sc_od1))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od1[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)
    self.assertEquals(3, len(new_sc_od2))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od2[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)

    self._assertDirInfoEqual(new_di1, new_di2)

  def testSyncNewFileRight(self):
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()

    new_sc_od1, new_sc_od2, new_di1, new_di2 = self._merge_for_test()

    self.assertEquals(3, len(new_sc_od1))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od1[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)
    self.assertEquals(3, len(new_sc_od2))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od2[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)

    self._assertDirInfoEqual(new_di1, new_di2)

  def testSyncNewFileConflict(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE_NEW), 'w')
    f.write('new1')
    f.close()
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE_NEW), 'w')
    f.write('new2')
    f.close()

    new_sc_od1, new_sc_od2, new_di1, new_di2 = self._merge_for_test()

    self.assertEquals(3, len(new_sc_od1))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od1[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)
    self.assertEquals(3, len(new_sc_od2))
    self.assertEquals(
        change_entry.CONTENT_STATUS_NEW,
        new_sc_od2[os.path.join('.', _TEST_CASE_FILE_NEW)]
            .change.content_status)

    self._assertDirInfoEqual(new_di1, new_di2)

