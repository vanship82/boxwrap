import collections
import inspect
import os
import shutil
import unittest

import cStringIO

from sync import merge
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

_TEST_INITIAL_CONTENT = 'test'


class TestMergeFiles(unittest.TestCase):

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

    self.dir_info1 = file_info.load_rel_dir_info(_TEST_DIR1)
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.dir_info1 = change_entry.apply_dir_changes_to_dir_info(
        '.',  # use current dir as base dir
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_DIR1),
            self.dir_info1, root_dir=_TEST_DIR1, tmp_dir=_TEST_TMP))

    self.dir_info2 = file_info.load_rel_dir_info(_TEST_DIR2)
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.dir_info2 = change_entry.apply_dir_changes_to_dir_info(
        '.',  # use current dir as base dir
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_DIR2),
            self.dir_info2, root_dir=_TEST_DIR2, tmp_dir=_TEST_TMP))
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.mkdir(_TEST_TMP)

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  # TODO: use this method to verify the final state
  def _assertDirInfoEqual(self, dir_info1, dir_info2):
    for fi1, fi2 in util.merge_two_iterators(
        dir_info1.flat_file_info_list(), dir_info2.flat_file_info_list(),
        key_func=lambda x: x.path_for_sorting()):
      self.assertIsNotNone(fi1)
      self.assertIsNotNone(fi2)
      self.assertEquals(fi1.path, fi2.path)
      self.assertEquals(fi1.is_dir, fi2.is_dir)
      self.assertFalse(fi1.is_modified(fi2))

  def _assertContentStatus(self, expected_status, dir_changes, path):
    split_paths = path.split(os.sep)
    dc = dir_changes
    for i in range(0, len(split_paths)-1):
      dc = dc.dir_changes(os.sep.join(split_paths[:i + 1]))
    self.assertEquals(expected_status, dc.change(path).content_status)

  def _merge_for_test(self):
    self.dir_changes1 = change_entry.get_dir_changes(
        file_info.load_rel_dir_info(_TEST_DIR1),
        self.dir_info1, root_dir=_TEST_DIR1, tmp_dir=_TEST_TMP)
    self.dir_changes2 = change_entry.get_dir_changes(
        file_info.load_rel_dir_info(_TEST_DIR2),
        self.dir_info2, root_dir=_TEST_DIR2, tmp_dir=_TEST_TMP)

    result = merge.merge(self.dir_changes1, self.dir_changes2)
    self.dc_new1 = result[0]
    self.changes_new1 = [x for x in self.dc_new1.flat_changes()]
    self.di_new1 = change_entry.apply_dir_changes_to_dir_info('.',
                                                              self.dc_new1)
    self.dc_old1 = result[1]
    self.changes_old1 = [x for x in self.dc_old1.flat_changes()]
    self.di_old1 = change_entry.apply_dir_changes_to_dir_info('.',
                                                              self.dc_old1)
    self.dc_new2 = result[2]
    self.changes_new2 = [x for x in self.dc_new2.flat_changes()]
    self.di_new2 = change_entry.apply_dir_changes_to_dir_info('.',
                                                              self.dc_new2)
    self.dc_old2 = result[3]
    self.changes_old2 = [x for x in self.dc_old2.flat_changes()]
    self.di_old2 = change_entry.apply_dir_changes_to_dir_info('.',
                                                              self.dc_old2)
    self.dc_conflict = result[4]
    self.changes_conflict = [x for x in self.dc_conflict.flat_changes()]

  def _print_changes(self):
    print "dc_new1"
    for x in self.changes_new1:
      print x
    print "dc_old1"
    for x in self.changes_old1:
      print x
    print "dc_new2"
    for x in self.changes_new2:
      print x
    print "dc_old2"
    for x in self.changes_old2:
      print x

  def testInitialSync(self):
    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1, os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_old1, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_old1, os.path.join('.', _TEST_CASE_FILE))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2, os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_old2, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_old2, os.path.join('.', _TEST_CASE_FILE))

  def testSyncNewFileLeft(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()

    self._merge_for_test()

    self.assertEquals(3, len(self.changes_new1))
    self.assertEquals(3, len(self.changes_old1))
    self.assertEquals(3, len(self.changes_new2))
    self.assertEquals(3, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))

  def testSyncNewFileRight(self):
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()

    self._merge_for_test()

    self.assertEquals(3, len(self.changes_new1))
    self.assertEquals(3, len(self.changes_old1))
    self.assertEquals(3, len(self.changes_new2))
    self.assertEquals(3, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))

  def testSyncNewFileConflict(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE_NEW), 'w')
    f.write('new1')
    f.close()
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE_NEW), 'w')
    f.write('new2')
    f.close()

    self._merge_for_test()

    self.assertEquals(3, len(self.changes_new1))
    self.assertEquals(3, len(self.changes_old1))
    self.assertEquals(3, len(self.changes_new2))
    self.assertEquals(3, len(self.changes_old2))
    self.assertEquals(2, len(self.changes_conflict))

    self.assertFalse(
        self.dc_new2
            .change('.').dir_changes
            .change(os.path.join('.',  _TEST_CASE_FILE_NEW))
            .conflict_info.is_modified(
                self.dc_conflict
                    .change('.').dir_changes
                    .change(os.path.join('.', _TEST_CASE_FILE_NEW))
                    .cur_info))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_conflict, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_conflict,
                              os.path.join('.', _TEST_CASE_FILE_NEW))

  def testSyncNewFileSame(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE_NEW), 'w')
    f.write('new1')
    f.close()
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE_NEW), 'w')
    f.write('new1')
    f.close()

    self._merge_for_test()

    self.assertEquals(3, len(self.changes_new1))
    self.assertEquals(3, len(self.changes_old1))
    self.assertEquals(3, len(self.changes_new2))
    self.assertEquals(3, len(self.changes_old2))
    self.assertEquals(0, len(self.changes_conflict))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE_NEW))

  def testSyncModifiedFileLeft(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncModifiedFileRight(self):
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncModifiedFileConflict(self):
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE), 'w')
    f.write('modified1')
    f.close()
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE), 'w')
    f.write('modified2')
    f.close()

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))
    self.assertEquals(2, len(self.changes_conflict))

    self.assertFalse(
        self.dc_new2
            .change('.').dir_changes
            .change(os.path.join('.',  _TEST_CASE_FILE))
            .conflict_info.is_modified(
                self.dc_conflict
                    .change('.').dir_changes
                    .change(os.path.join('.', _TEST_CASE_FILE))
                    .cur_info))


    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_conflict, '.')
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_conflict,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncDeleteFileLeft(self):
    os.remove(os.path.join(_TEST_DIR1, _TEST_CASE_FILE))

    self._merge_for_test()

    self.assertEquals(1, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncDeleteFileRight(self):
    os.remove(os.path.join(_TEST_DIR2, _TEST_CASE_FILE))

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(1, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncDeleteFileBoth(self):
    os.remove(os.path.join(_TEST_DIR1, _TEST_CASE_FILE))
    os.remove(os.path.join(_TEST_DIR2, _TEST_CASE_FILE))

    self._merge_for_test()

    self.assertEquals(1, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(1, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_DELETED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncDeleteFileLeftModifyRight(self):
    os.remove(os.path.join(_TEST_DIR1, _TEST_CASE_FILE))
    f = open(os.path.join(_TEST_DIR2, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

  def testSyncDeleteFileRightModifyLeft(self):
    os.remove(os.path.join(_TEST_DIR2, _TEST_CASE_FILE))
    f = open(os.path.join(_TEST_DIR1, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()

    self._merge_for_test()

    self.assertEquals(2, len(self.changes_new1))
    self.assertEquals(2, len(self.changes_old1))
    self.assertEquals(2, len(self.changes_new2))
    self.assertEquals(2, len(self.changes_old2))

    self._assertContentStatus(change_entry.CONTENT_STATUS_NO_CHANGE,
                              self.dc_new1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old1,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_NEW,
                              self.dc_new2,
                              os.path.join('.', _TEST_CASE_FILE))
    self._assertContentStatus(change_entry.CONTENT_STATUS_MODIFIED,
                              self.dc_old2,
                              os.path.join('.', _TEST_CASE_FILE))

