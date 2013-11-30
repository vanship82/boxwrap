import collections
import inspect
import os
import shutil
import unittest

import cStringIO

from sync import file_info
from sync import change_entry

_TEST_TMP_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_tmp')
_TEST_SRC = os.path.join(_TEST_TMP_BASE_DIR, 'src')
_TEST_TMP = os.path.join(_TEST_TMP_BASE_DIR, 'tmp')
_TEST_CASE_FILE = 'test.txt'
_TEST_CASE_FILE_NEW = 'test_new.txt'
_TEST_CASE_DIR = 'test_dir'
_TEST_CASE_DIR_NEW = 'test_dir_new'

_TEST_INITIAL_CONTENT = 'test'


class TestSyncFile(unittest.TestCase):

  def setUp(self):
    try:
      shutil.rmtree(_TEST_SRC)
    except:
      pass
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.makedirs(_TEST_SRC)
    os.makedirs(_TEST_TMP)

    self.dir_info = file_info.load_rel_dir_info(_TEST_SRC)
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.dir_info = change_entry.apply_dir_changes_to_dir_info(
        '.',  # use current dir as base dir
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_SRC),
            self.dir_info, root_dir=_TEST_SRC, tmp_dir=_TEST_TMP))
    self.file_info_list = [x for x in self.dir_info.flat_file_info_list()]
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.mkdir(_TEST_TMP)

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  def _test_get_file_info_list_after_sync(self):
    self.dir_info = change_entry.apply_dir_changes_to_dir_info(
        '.',
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_SRC),
            self.dir_info, root_dir=_TEST_SRC, tmp_dir=_TEST_TMP))
    self.file_info_list = [x for x in self.dir_info.flat_file_info_list()]

  def testInitialSync(self):
    self.assertEquals(2, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE),
        self.file_info_list[1].path)

  def testSyncModifyFile(self):
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()
    self._test_get_file_info_list_after_sync()
    self.assertEquals(2, len(self.file_info_list))
    self.assertIsNotNone(self.file_info_list[1].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.file_info_list[1].tmp_file))

  def testSyncDeleteFile(self):
    os.remove(os.path.join(_TEST_SRC, _TEST_CASE_FILE))
    self._test_get_file_info_list_after_sync()
    self.assertEquals(1, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)

  def testSyncNewFile(self):
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()
    self._test_get_file_info_list_after_sync()
    self.assertEquals(3, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE),
        self.file_info_list[1].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE_NEW),
        self.file_info_list[2].path)
    self.assertIsNotNone(self.file_info_list[2].tmp_file)
    self._assertFileContent(
        'new', os.path.join(_TEST_TMP, self.file_info_list[2].tmp_file))


class TestSyncDir(unittest.TestCase):

  def setUp(self):
    try:
      shutil.rmtree(_TEST_SRC)
    except:
      pass
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.makedirs(_TEST_SRC)
    os.makedirs(_TEST_TMP)

    self.dir_info = file_info.load_rel_dir_info(_TEST_SRC)
    self.test_dir = os.path.join(_TEST_SRC, _TEST_CASE_DIR)
    os.makedirs(self.test_dir)
    f = open(os.path.join(self.test_dir, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.dir_info = change_entry.apply_dir_changes_to_dir_info(
        '.',  # use current dir as base dir
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_SRC),
            self.dir_info, root_dir=_TEST_SRC, tmp_dir=_TEST_TMP))
    self.file_info_list = [x for x in self.dir_info.flat_file_info_list()]
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.mkdir(_TEST_TMP)

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  def _test_get_file_info_list_after_sync(self):
    self.dir_info = change_entry.apply_dir_changes_to_dir_info(
        '.',
        change_entry.get_dir_changes(
            file_info.load_rel_dir_info(_TEST_SRC),
            self.dir_info, root_dir=_TEST_SRC, tmp_dir=_TEST_TMP))
    self.file_info_list = [x for x in self.dir_info.flat_file_info_list()]

  def testInitialSync(self):
    self.assertEquals(3, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.file_info_list[1].path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.file_info_list[2].path)

  def testSyncModifyFileInDir(self):
    f = open(os.path.join(self.test_dir, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()
    self._test_get_file_info_list_after_sync()
    self.assertIsNotNone(self.file_info_list[2].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.file_info_list[2].tmp_file))

  def testSyncDeleteDir(self):
    shutil.rmtree(os.path.join(_TEST_SRC, _TEST_CASE_DIR))
    self._test_get_file_info_list_after_sync()
    self.assertEquals(1, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)

  def testSyncDirToFile(self):
    shutil.rmtree(os.path.join(_TEST_SRC, _TEST_CASE_DIR))
    f = open(self.test_dir, 'w')
    f.write('modified')
    f.close()
    self._test_get_file_info_list_after_sync()
    self.assertEquals(2, len(self.file_info_list))
    self.assertIsNotNone(self.file_info_list[1].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.file_info_list[1].tmp_file))

  def testSyncFileToDir(self):
    os.remove(os.path.join(self.test_dir, _TEST_CASE_FILE))
    os.mkdir(os.path.join(self.test_dir, _TEST_CASE_FILE))
    self._test_get_file_info_list_after_sync()
    self.assertEquals(3, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.file_info_list[1].path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.file_info_list[2].path)
    self.assertTrue(self.file_info_list[2].is_dir)
    self.assertIsNone(self.file_info_list[2].tmp_file)

  def testSyncNewDir(self):
    os.mkdir(os.path.join(_TEST_SRC, _TEST_CASE_DIR_NEW))
    self._test_get_file_info_list_after_sync()
    self.assertEquals(4, len(self.file_info_list))
    self.assertEquals('.', self.file_info_list[0].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.file_info_list[1].path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.file_info_list[2].path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR_NEW),
        self.file_info_list[3].path)
    self.assertTrue(self.file_info_list[3].is_dir)
    self.assertIsNone(self.file_info_list[3].tmp_file)

