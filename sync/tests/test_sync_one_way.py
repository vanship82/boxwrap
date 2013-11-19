import collections
import inspect
import os
import shutil
import unittest

import cStringIO

from sync import sync_one_way
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

    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC, file_info.empty_dir_info(_TEST_SRC), _TEST_TMP)
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
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

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  def testInitialSync(self):
    self.assertEquals(2, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE),
        self.sync_file_info_list[1].file_info.path)

  def testSyncModifyFile(self):
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(2, len(self.sync_file_info_list))
    self.assertIsNotNone(self.sync_file_info_list[1].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.sync_file_info_list[1].tmp_file))

  def testSyncDeleteFile(self):
    os.remove(os.path.join(_TEST_SRC, _TEST_CASE_FILE))
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(1, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)

  def testSyncNewFile(self):
    f = open(os.path.join(_TEST_SRC, _TEST_CASE_FILE_NEW), 'w')
    f.write('new')
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(3, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE),
        self.sync_file_info_list[1].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_FILE_NEW),
        self.sync_file_info_list[2].file_info.path)
    self.assertIsNotNone(self.sync_file_info_list[2].tmp_file)
    self._assertFileContent(
        'new', os.path.join(_TEST_TMP, self.sync_file_info_list[2].tmp_file))


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

    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC, file_info.empty_dir_info(_TEST_SRC), _TEST_TMP)
    self.test_dir = os.path.join(_TEST_SRC, _TEST_CASE_DIR)
    os.makedirs(self.test_dir)
    f = open(os.path.join(self.test_dir, _TEST_CASE_FILE), 'w')
    f.write(_TEST_INITIAL_CONTENT)
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
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

  def _assertFileContent(self, content, file_path):
    with open(file_path, 'r') as f:
      self.assertEquals(content, f.read())

  def testInitialSync(self):
    self.assertEquals(3, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.sync_file_info_list[1].file_info.path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.sync_file_info_list[2].file_info.path)

  def testSyncModifyFileInDir(self):
    f = open(os.path.join(self.test_dir, _TEST_CASE_FILE), 'w')
    f.write('modified')
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertIsNotNone(self.sync_file_info_list[2].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.sync_file_info_list[2].tmp_file))

  def testSyncDeleteDir(self):
    shutil.rmtree(os.path.join(_TEST_SRC, _TEST_CASE_DIR))
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(1, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)

  def testSyncDirToFile(self):
    shutil.rmtree(os.path.join(_TEST_SRC, _TEST_CASE_DIR))
    f = open(self.test_dir, 'w')
    f.write('modified')
    f.close()
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(2, len(self.sync_file_info_list))
    self.assertIsNotNone(self.sync_file_info_list[1].tmp_file)
    self._assertFileContent(
        'modified',
        os.path.join(_TEST_TMP, self.sync_file_info_list[1].tmp_file))

  def testSyncFileToDir(self):
    os.remove(os.path.join(self.test_dir, _TEST_CASE_FILE))
    os.mkdir(os.path.join(self.test_dir, _TEST_CASE_FILE))
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(3, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.sync_file_info_list[1].file_info.path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.sync_file_info_list[2].file_info.path)
    self.assertTrue(self.sync_file_info_list[2].file_info.is_dir)
    self.assertIsNone(self.sync_file_info_list[2].tmp_file)

  def testSyncNewDir(self):
    os.mkdir(os.path.join(_TEST_SRC, _TEST_CASE_DIR_NEW))
    self.sync_file_info_list = self._get_sync_file_info_list(
        _TEST_SRC,
        self._get_sync_dir_info(_TEST_SRC, self.sync_file_info_list),
        _TEST_TMP)
    self.assertEquals(4, len(self.sync_file_info_list))
    self.assertEquals('.', self.sync_file_info_list[0].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR),
        self.sync_file_info_list[1].file_info.path)
    self.assertEquals(
        os.path.join('.', os.path.join(_TEST_CASE_DIR, _TEST_CASE_FILE)),
        self.sync_file_info_list[2].file_info.path)
    self.assertEquals(
        os.path.join('.', _TEST_CASE_DIR_NEW),
        self.sync_file_info_list[3].file_info.path)
    self.assertTrue(self.sync_file_info_list[3].file_info.is_dir)
    self.assertIsNone(self.sync_file_info_list[3].tmp_file)

