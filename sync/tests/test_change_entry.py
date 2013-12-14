import inspect
import os
import shutil
import unittest

import cStringIO

from sync import file_info
from sync import change_entry

_TEST_CASES_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_cases')
_TEST_CASES_SRC = 'src'
_TEST_CASES_DEST = 'dest'

_TEST_TMP_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_tmp')
_TEST_SRC = os.path.join(_TEST_TMP_BASE_DIR, _TEST_CASES_SRC)
_TEST_DEST = os.path.join(_TEST_TMP_BASE_DIR, _TEST_CASES_DEST)
_TEST_TMP = os.path.join(_TEST_TMP_BASE_DIR, 'tmp')


class TestChangeEntry(unittest.TestCase):

  def setUp(self):
    try:
      shutil.rmtree(_TEST_SRC)
    except:
      pass
    try:
      shutil.rmtree(_TEST_DEST)
    except:
      pass
    try:
      shutil.rmtree(_TEST_TMP)
    except:
      pass
    os.makedirs(_TEST_TMP)
    shutil.copytree(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_SRC),
                    _TEST_SRC)
    shutil.copytree(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_DEST),
                    _TEST_DEST)

    self._old_cwd = os.getcwd()

  def tearDown(self):
    os.chdir(self._old_cwd)

  def test_change_entry(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old)
    di_final = change_entry.apply_dir_changes_to_dir_info('.', dc)
    ''' debug only
    print "***************** dir_changes"
    for item in dc.flat_changes():
      print item
    print "***************** final dir_info"
    for item in di_final.flat_file_info_list():
      print item
    '''
    dc_final = change_entry.get_dir_changes(di_new, di_final)
    for item in dc_final.flat_changes():
      self.assertEquals(change_entry.CONTENT_STATUS_NO_CHANGE,
                        item.content_status)

