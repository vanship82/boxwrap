import inspect
import os
import shutil
import unittest

from sync import change_entry
import compression
from sync import file_info
import main

_TEST_CASES_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'cases', 'boxwrap')
_TEST_TMP_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_tmp')
_TEST_WORKING = os.path.join(_TEST_TMP_BASE_DIR, 'working')
_TEST_CLOUD = os.path.join(_TEST_TMP_BASE_DIR, 'cloud')
_TEST_TMP = os.path.join(_TEST_TMP_BASE_DIR, 'tmp')
_TEST_FI_CSV = os.path.join(_TEST_TMP_BASE_DIR, 'fi.csv')

''' Test boxwrap simple
'''
class TestMain(unittest.TestCase):

  def setUp(self):
    try:
      shutil.rmtree(_TEST_WORKING)
    except:
      pass
    try:
      shutil.rmtree(_TEST_CLOUD)
    except:
      pass
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    if not os.path.exists(_TEST_TMP_BASE_DIR):
      os.makedirs(_TEST_TMP_BASE_DIR)
    os.makedirs(_TEST_TMP)
    if os.path.exists(_TEST_FI_CSV):
      os.remove(_TEST_FI_CSV)
    shutil.copytree(os.path.join(_TEST_CASES_BASE_DIR, 'working'),
                    _TEST_WORKING)
    os.makedirs(_TEST_CLOUD)

    self.under_test = main.BoxWrap(_TEST_WORKING, _TEST_CLOUD, _TEST_TMP,
                                   _TEST_FI_CSV, password='123456')

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(
        file_info.empty_dir_info('.')))

    # Clean up tmp for initial sync
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.makedirs(_TEST_TMP)

  def _assertFileContent(self, content, file_path, debug=False):
    with open(file_path, 'r') as f:
      if debug:
        return content == f.read()
      else:
        self.assertEquals(content, f.read())

  # special_cases is
  # [([dir1, dir2, ..., filename], content_status, content)]
  # where content is optional
  def _assertDirChanges(self, dc, special_cases=None, debug=False):
    sc_dict = {}
    if special_cases:
      for case in special_cases:
        args = case[0]
        sc_dict[os.path.join(*args)] = case
    failure_count = 0
    for item in dc.flat_changes():
      is_failed = False
      if item.path in sc_dict:
        case = sc_dict[item.path]
        if debug:
          if not is_failed and case[1] != item.content_status:
            is_failed = True
        else:
          self.assertEquals(case[1], item.content_status)

        if len(case) > 2:
          if debug:
            if (not is_failed
                and not self._assertFileContent(
                    case[2], item.path, debug=True)):
              is_failed = True
          else:
            self._assertFileContent(case[2], item.path)

        if debug:
          if is_failed:
            failure_count += 1
            print 'Error item %d: %s' % (failure_count, item)
      else:
        if debug:
          if item.content_status != change_entry.CONTENT_STATUS_NO_CHANGE:
            failure_count += 1
            print 'Error item %d: %s' % (failure_count, item)
        else:
          self.assertEquals(change_entry.CONTENT_STATUS_NO_CHANGE,
                            item.content_status,
                            'Error item: %s' % item)
    self.assertEquals(0, failure_count)

  def _print_changes(self, name, dir_changes):
    print name
    for x in dir_changes.flat_changes():
      print x
      print '    cur_info: %s' % x.cur_info
      print '    old_info: %s' % x.old_info

  def _print_di(self, name, dir_info):
    print name
    for x in dir_info.flat_file_info_list():
      print x

  def testInitialSync(self):
    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertFalse(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)
    self.assertIsNotNone(
        self.working_di.get(os.path.join('.', 'test1.txt'))
            .compressed_file_info)

  def testSyncWorkingFileNewModifyDelete(self):
    f = open(os.path.join(_TEST_WORKING, 'test_new.txt'), 'w')
    f.write('test_new')
    f.close()
    f = open(os.path.join(_TEST_WORKING, 'dir1', 'test1_1.txt'), 'w')
    f.write('test_modified')
    f.close()
    os.remove(os.path.join(_TEST_WORKING, 'test1.txt'))

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

  def testSyncCloudFileNewModifyDelete(self):
    shutil.move(
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'dir1', 'test1_1.txt')),
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'test_new.txt')))
    shutil.move(
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'test1.txt')),
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'dir1', 'test1_1.txt')))

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di, debug=False))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)
    self.assertFalse(os.path.exists(
        os.path.join(_TEST_WORKING, 'test1.txt')))
    self._assertFileContent(
        'test1_1\n', os.path.join(_TEST_WORKING, 'test_new.txt'))
    self._assertFileContent(
        'test1\n', os.path.join(_TEST_WORKING, 'dir1', 'test1_1.txt'))

  def testSyncConflictBothModify(self):
    f = open(os.path.join(_TEST_WORKING, 'test1.txt'), 'w')
    f.write('test_modified')
    f.close()
    shutil.copy(
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'dir1', 'test1_1.txt')),
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'test1.txt')))

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

    self._assertFileContent(
        'test_modified', os.path.join(_TEST_WORKING, 'test1.txt'))
    self._assertFileContent(
        'test1_1\n', os.path.join(_TEST_WORKING, 'test1 (conflict copy 1).txt'))

  def testSyncConflictBothNew(self):
    f = open(os.path.join(_TEST_WORKING, 'test_new.txt'), 'w')
    f.write('test_new')
    f.close()
    shutil.copy(
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'dir1', 'test1_1.txt')),
        compression.get_compressed_filename(
            os.path.join(_TEST_CLOUD, 'test_new.txt')))

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

    self._assertFileContent(
        'test_new', os.path.join(_TEST_WORKING, 'test_new.txt'))
    self._assertFileContent(
        'test1_1\n',
        os.path.join(_TEST_WORKING, 'test_new (conflict copy 1).txt'))

  def testSyncCloudDirNewDelete(self):
    shutil.move(
        os.path.join(_TEST_CLOUD, 'dir1'),
        os.path.join(_TEST_CLOUD, 'dir2'))

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di, debug=False))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)
    self._assertFileContent(
        'test1_1\n', os.path.join(_TEST_WORKING, 'dir2', 'test1_1.txt'))

  def testInvalidArchiveNotCompressedFilename(self):
    # Add new file not compressed and without compressed filename
    f = open(os.path.join(_TEST_CLOUD, 'test_new.txt'), 'w')
    f.write('test_new')
    f.close()

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

    self._assertFileContent(
        'test_new', os.path.join(_TEST_WORKING, 'test_new.txt'))
    self.assertFalse(os.path.exists(os.path.join(_TEST_CLOUD, 'test_new.txt')))

  def testInvalidArchive(self):
    # Add new file with compressed filename but not a valid compressed file
    compressed_filename = compression.get_compressed_filename('test_new.txt')
    f = open(os.path.join(_TEST_CLOUD, compressed_filename), 'w')
    f.write('test_new')
    f.close()

    has_changes, self.working_di, self.cloud_di = (
        self.under_test.sync(self.working_di))
    self.assertTrue(has_changes)

    dc = change_entry.get_dir_changes(self.cloud_di, self.working_di)
    self._assertDirChanges(dc, debug=True)

    self._assertFileContent('test_new',
                            os.path.join(_TEST_WORKING, compressed_filename))
    self.assertFalse(
        os.path.exists(os.path.join(_TEST_CLOUD, compressed_filename)))

