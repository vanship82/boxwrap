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


def _set_file_time(filename, t):
  os.utime(filename, (t, t))


class TestUnisonDirectoryCases(unittest.TestCase):

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

    t = int(time.time())
    _write_file(_CASE_SRC_FILE, '123')
    _write_file(_CASE_DEST_FILE, '123')
    os.chmod(_CASE_SRC_FILE, _MOD_NORMAL)
    os.chmod(_CASE_DEST_FILE, _MOD_NORMAL)
    _set_file_time(_CASE_SRC_FILE, t)
    _set_file_time(_CASE_DEST_FILE, t)

    _write_file(_CASE_SRC_FILE + '.bak', '123')
    _write_file(_CASE_DEST_FILE + '.bak', '123')
    os.chmod(_CASE_SRC_FILE + '.bak', _MOD_NORMAL)
    os.chmod(_CASE_DEST_FILE + '.bak', _MOD_NORMAL)
    _set_file_time(_CASE_SRC_FILE + '.bak', t)
    _set_file_time(_CASE_DEST_FILE + '.bak', t)

    os.makedirs(_CASE_SRC_DIR)
    os.makedirs(_CASE_DEST_DIR)

    _write_file(_CASE_SRC_DIR_FILE, '123')
    _write_file(_CASE_DEST_DIR_FILE, '123')
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_NORMAL)
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_NORMAL)
    _set_file_time(_CASE_SRC_DIR_FILE, t)
    _set_file_time(_CASE_DEST_DIR_FILE, t)

    _initial_sync()

  def test_src_to_dest_update(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_but_same_update(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_update_but_no_change(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _write_file(_CASE_SRC_DIR_FILE, '123')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))


  def test_src_to_dest_update_force_src(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_force_dest(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_chmod(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_chmod_not_synced(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        perms=unison.PERMS_NONE)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_chmod_force_src(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_chmod_force_dest(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_time(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_time_force_src(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_time_force_dest(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete(self):
    os.remove(_CASE_SRC_DIR_FILE)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_force_src(self):
    os.remove(_CASE_SRC_DIR_FILE)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_force_dest(self):
    os.remove(_CASE_SRC_DIR_FILE)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_conflict(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_update_conflict_force_src(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_conflict_force_dest(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_chmod_conflict(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_chmod_conflict_force_src(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_chmod_conflict_force_dest(self):
    os.chmod(_CASE_SRC_DIR_FILE, _MOD_ALL)
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_time_conflict(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_time_conflict_force_src(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_time_conflict_force_dest(self):
    _set_file_time(_CASE_SRC_DIR_FILE, int(time.time() - 300))
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_PROPERTIES,
                     cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_chmod_conflict(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_update_chmod_conflict_force_src(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_chmod_conflict_force_dest(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    os.chmod(_CASE_DEST_DIR_FILE, _MOD_OWNER)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_time_conflict(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_update_time_conflict_force_src(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_update_time_conflict_force_dest(self):
    _write_file(_CASE_SRC_DIR_FILE, '1234')
    _set_file_time(_CASE_DEST_DIR_FILE, int(time.time() - 500))
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON, times=True,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_UPDATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE, _CASE_SRC), cl[0].path)

  def test_src_to_dest_new(self):
    _write_file(_CASE_SRC_DIR_FILE + '.bak', '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE + '.bak', _CASE_SRC), cl[0].path)

  def test_src_to_dest_new_force_src(self):
    _write_file(_CASE_SRC_DIR_FILE + '.bak', '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE + '.bak', _CASE_SRC), cl[0].path)

  def test_src_to_dest_new_force_dest(self):
    _write_file(_CASE_SRC_DIR_FILE + '.bak', '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR_FILE + '.bak', _CASE_SRC), cl[0].path)

  def test_src_to_dest_new_dir(self):
    os.makedirs(os.path.join(_CASE_SRC_DIR, 'testdir2'))
    _write_file(
      os.path.join(os.path.join(_CASE_SRC_DIR, 'testdir2'), 'testifile.txt'),
      '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(
      os.path.relpath(os.path.join(_CASE_SRC_DIR, 'testdir2'), _CASE_SRC),
      cl[0].path)

  def test_src_to_dest_new_dir_force_src(self):
    os.makedirs(os.path.join(_CASE_SRC_DIR, 'testdir2'))
    _write_file(
      os.path.join(os.path.join(_CASE_SRC_DIR, 'testdir2'), 'testifile.txt'),
      '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(
      os.path.relpath(os.path.join(_CASE_SRC_DIR, 'testdir2'), _CASE_SRC),
      cl[0].path)

  def test_src_to_dest_new_dir_force_dest(self):
    os.makedirs(os.path.join(_CASE_SRC_DIR, 'testdir2'))
    _write_file(
      os.path.join(os.path.join(_CASE_SRC_DIR, 'testdir2'), 'testifile.txt'),
      '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(
      os.path.relpath(os.path.join(_CASE_SRC_DIR, 'testdir2'), _CASE_SRC),
      cl[0].path)

  def test_src_to_dest_delete_dir(self):
    shutil.rmtree(_CASE_SRC_DIR)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_force_src(self):
    shutil.rmtree(_CASE_SRC_DIR)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_force_dest(self):
    shutil.rmtree(_CASE_SRC_DIR)
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_dir_replace_by_file(self):
    # Note that if a dir is replaced by a file or vice versa, it is treated as
    # OPERATION_CREATE, not OPERATION_UPDATE
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_dir_replace_by_file_force_src(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_dir_replace_by_file_force_dest(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_conflict_change(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_delete_dir_conflict_change_force_src(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_conflict_change_force_dest(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_conflict_replace_by_file(self):
    shutil.rmtree(_CASE_SRC_DIR)
    shutil.rmtree(_CASE_DEST_DIR)
    _write_file(_CASE_DEST_DIR, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_delete_dir_conflict_replace_by_file_force_src(self):
    shutil.rmtree(_CASE_SRC_DIR)
    shutil.rmtree(_CASE_DEST_DIR)
    _write_file(_CASE_DEST_DIR, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_DELETE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_delete_dir_conflict_replace_by_file_force_dest(self):
    shutil.rmtree(_CASE_SRC_DIR)
    shutil.rmtree(_CASE_DEST_DIR)
    _write_file(_CASE_DEST_DIR, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)


  def test_src_to_dest_dir_replace_by_file_conflict_change(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON)
    self.assertEqual(0, len(cl))

  def test_src_to_dest_dir_replace_by_file_conflict_change_force_src(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_SRC)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_DEST, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)

  def test_src_to_dest_dir_replace_by_file_conflict_change_force_dest(self):
    shutil.rmtree(_CASE_SRC_DIR)
    _write_file(_CASE_SRC_DIR, '1234')
    _write_file(_CASE_DEST_DIR_FILE, '12345')
    cl = unison.sync_with_unison(
        _CASE_SRC, _CASE_DEST, unison_path=_CASE_UNISON,
        force_dir=_CASE_DEST)
    self.assertEqual(1, len(cl))
    self.assertEqual(unison.PathChangeStatus.OPERATION_CREATE, cl[0].operation)
    self.assertEqual(unison.PathChangeStatus.TARGET_SRC, cl[0].target)
    self.assertEqual(os.path.relpath(_CASE_SRC_DIR, _CASE_SRC), cl[0].path)


