import inspect
import os
import shutil
import stat
import time
import unittest
import unison

_CASE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    os.path.join('cases', 'unison'))
_CASE_SRC = os.path.join(_CASE_BASE_DIR, 'src')
_CASE_DEST = os.path.join(_CASE_BASE_DIR, 'dest')
_CASE_UNISON = os.path.join(_CASE_BASE_DIR, '.unison')

_CASE_SRC_FILE = os.path.join(_CASE_SRC, 'test.txt')
_CASE_DEST_FILE = os.path.join(_CASE_DEST, 'test.txt')
_CASE_SRC_DIR = os.path.join(_CASE_SRC, 'testdir')
_CASE_DEST_DIR = os.path.join(_CASE_DEST, 'testdir')
_CASE_SRC_DIR_FILE = os.path.join(_CASE_SRC_DIR, 'testdirfile.txt')
_CASE_DEST_DIR_FILE = os.path.join(_CASE_DEST_DIR, 'testdirfile.txt')

_MOD_NORMAL = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
_MOD_ALL = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP |
    stat.S_IROTH | stat.S_IWOTH)
_MOD_OWNER = stat.S_IRUSR | stat.S_IWUSR


def _initial_sync():
  if os.path.exists(_CASE_UNISON):
    shutil.rmtree(_CASE_UNISON)
  unison.sync_with_unison(
      _CASE_SRC,
      _CASE_DEST,
      times=True, perms=unison.PERMS_DEFAULT,
      unison_path=_CASE_UNISON)


def _write_file(filename, content):
  f = open(filename, 'w')
  f.write(content)
  f.close()


class TestUnisonCreateCases(unittest.TestCase):

  def setUp(self):
    if os.path.exists(_CASE_SRC):
      shutil.rmtree(_CASE_SRC)
    if os.path.exists(_CASE_DEST):
      shutil.rmtree(_CASE_DEST)
    if os.path.exists(_CASE_UNISON):
      shutil.rmtree(_CASE_UNISON)
    os.makedirs(_CASE_SRC)
    os.makedirs(_CASE_DEST)
    _initial_sync()

  def test_src_to_dest_none(self):
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_new(self):
    _write_file(_CASE_SRC_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_FILE), cl[0].path)

  def test_src_to_dest_new_force_src(self):
    _write_file(_CASE_SRC_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_FILE), cl[0].path)

  def test_src_to_dest_new_force_dest(self):
    _write_file(_CASE_SRC_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_FILE), cl[0].path)

  def test_src_to_dest_new_dir(self):
    os.makedirs(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_DIR), cl[0].path)

  def test_src_to_dest_new_dir_force_src(self):
    os.makedirs(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_DIR), cl[0].path)

  def test_src_to_dest_new_dir_force_dest(self):
    os.makedirs(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.basename(_CASE_SRC_DIR), cl[0].path)

