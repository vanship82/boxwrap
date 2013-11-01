import inspect
import os
import unittest

import cStringIO

from dir import file_entry
from dir import change_status

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

  def test_change_status(self):
    os.chdir(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_DEST))
    entries_new = file_entry.load_dir_recursively('.')
    os.chdir(os.path.join(_TEST_CASES_BASE_DIR, _TEST_CASES_SRC))
    entries_old = file_entry.load_dir_recursively('.')
    result = change_status.get_change_status(entries_new, entries_old)
    for path, item in result.iteritems():
      print '******************* %s, %s' % (item.path, item.content_status)
      print '       new: %s' % item.new_entry
      print '       old: %s' % item.old_entry

