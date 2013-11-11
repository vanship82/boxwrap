import inspect
import os
import unittest

import cStringIO

from dir import file_entry

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

  def test_load_dir_recursively(self):
    file_entries = file_entry.load_dir_recursively(_TEST_CASES_SRC)
    expected_file_entries_from_csv = file_entry.load_csv(
        open('expected_src_file_entries.csv', 'r'))
    self.assertEqual(len(expected_file_entries_from_csv), len(file_entries))
    for i in range(len(file_entries)):
      file_entries[i].calculate_hash()
      self._assert_file_entries_valid_and_equal(
          expected_file_entries_from_csv[i], file_entries[i])

  def test_csv_read_write(self):
    file_entries = file_entry.load_dir_recursively(_TEST_CASES_SRC)
    output = cStringIO.StringIO()
    file_entry.write_sorted_list_to_csv(file_entries, output)
    file_entries_from_csv = file_entry.load_csv(
        cStringIO.StringIO(output.getvalue()))
    self.assertEqual(len(file_entries), len(file_entries_from_csv))
    for i in range(len(file_entries)):
      self._assert_file_entries_valid_and_equal(
          file_entries[i], file_entries_from_csv[i])

  def _assert_file_entries_valid_and_equal(self, e1, e2):
    self.assertEqual(e1.path, e2.path)
    self.assertEqual(e1.is_dir, e2.is_dir)
    self.assertEqual(e1.mode, e2.mode)
    self.assertEqual(e1.size, e2.size)
    self.assertEqual(e1.file_hash, e2.file_hash)

    if e1.is_dir:
      self.assertIsNone(e1.size)
      self.assertIsNone(e2.size)
    else:
      self.assertTrue(e1.size >= 0)
      self.assertTrue(e2.size >= 0)

    self.assertTrue(e1.last_modified_time > 0)
    self.assertTrue(e2.last_modified_time > 0)

