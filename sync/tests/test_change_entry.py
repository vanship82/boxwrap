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
    entries_new = file_info.load_dir_recursively_and_sort('.')
    os.chdir(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_SRC))
    entries_old = file_info.load_dir_recursively_and_sort('.')
    for path, item in change_entry.get_change_entry(entries_new, entries_old):
      if item.parent_change_path:
        continue
      print item

