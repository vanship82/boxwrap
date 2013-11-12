import inspect
import os
import unittest

import cStringIO

from sync import file_info

_TEST_CASES_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    'test_cases')
_TEST_CASES_SRC = 'src'
_TEST_CASES_DEST = 'dest'


class TestFileInfo(unittest.TestCase):

  def setUp(self):
    self._old_cwd = os.getcwd()
    os.chdir(_TEST_CASES_BASE_DIR)

  def tearDown(self):
    os.chdir(self._old_cwd)

  def test_load_from_dir(self):
    file_info_list = (
        file_info.load_from_dir(_TEST_CASES_SRC).file_info_list())
    expected_file_info_list_from_csv =  (
        file_info
            .load_from_csv(open('expected_src_file_info_list.csv', 'r'))
            .file_info_list())
    self.assertEqual(len(expected_file_info_list_from_csv),
                     len(file_info_list))
    for i in range(len(file_info_list)):
      file_info_list[i].calculate_hash()
      self._assert_file_info_list_valid_and_equal(
          expected_file_info_list_from_csv[i], file_info_list[i])

  def test_csv_read_write(self):
    file_info_list = file_info.load_from_dir(_TEST_CASES_SRC)
    output = cStringIO.StringIO()
    file_info_list.write_to_csv(output)
    file_info_list_from_csv = file_info.load_from_csv(
        cStringIO.StringIO(output.getvalue()))

    file_info_list = file_info_list.file_info_list()
    file_info_list_from_csv = file_info_list_from_csv.file_info_list()
    self.assertEqual(len(file_info_list), len(file_info_list_from_csv))
    for i in range(len(file_info_list)):
      self._assert_file_info_list_valid_and_equal(
          file_info_list[i], file_info_list_from_csv[i])

  def _assert_file_info_list_valid_and_equal(self, e1, e2):
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

