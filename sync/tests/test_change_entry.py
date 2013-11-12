import inspect
import os
import unittest

import cStringIO

from sync import file_info
from sync import change_entry

_TEST_CASES_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_cases')
_TEST_CASES_SRC = 'src'
_TEST_CASES_DEST = 'dest'


class TestFileEntry(unittest.TestCase):

  def setUp(self):
    self._old_cwd = os.getcwd()
    os.chdir(_TEST_CASES_BASE_DIR)

  def tearDown(self):
    os.chdir(self._old_cwd)

  def test_change_entry(self):
    os.chdir(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_DEST))
    fil_new = file_info.load_from_dir('.')
    os.chdir(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_SRC))
    fil_old = file_info.load_from_dir('.')
    for path, item in change_entry.get_changes(fil_new, fil_old):
      if item.parent_change_path:
        continue
      print item

