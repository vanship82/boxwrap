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

_TEST_CONFLICT_CONTENT = 'conflict'


class TestChangeEntry(unittest.TestCase):

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

  def test_change_entry_applied_to_dir_info(self):
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
    self._assertDirChanges(dc_final)

  def test_change_entry_applied_to_real_dirs(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)
    ''' debug only
    print "***************** dir_changes"
    for item in dc.flat_changes():
      print item
    print "***************** final dir_info"
    for item in di_final.flat_file_info_list():
      print item
    '''
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_new, di_final)
    self._assertDirChanges(dc_final)

  def test_change_entry_conflict_file_new(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    f = open(os.path.join(_TEST_SRC, 'test8_new.txt'), 'w')
    # New file with different content, conflict
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()
    f = open(os.path.join(_TEST_SRC, 'dir2_modified', 'test2_8_new.txt'), 'w')
    # New file but same content, no conflict
    f.write('2_8\n')
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'test8_new (conflict copy 1).txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_file_modified(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    f = open(os.path.join(_TEST_SRC, 'test2_modified.txt'), 'w')
    # Modify file with different content, conflict
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()
    f = open(os.path.join(_TEST_SRC, 'dir2_modified', 'test2_2_modified.txt'),
             'w')
    # Modify file but same content, no conflict
    f.write('2_2\n')
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'test2_modified (conflict copy 1).txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_file_deleted(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    f = open(os.path.join(_TEST_SRC, 'test3_deleted.txt'), 'w')
    # Modify file to be deleted with different content, conflict
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()
    # Delete file already
    os.remove(os.path.join(_TEST_SRC, 'dir2_modified', 'test2_3_deleted.txt'))

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'test3_deleted.txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_dir_new(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    f = open(os.path.join(_TEST_SRC, 'dir11_new'), 'w')
    # New file, not a directory, conflict
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()
    # New dir, add a new file, no conflict
    os.mkdir(os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_11_new'))
    f = open(os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_11_new',
                          'test_conflict_new.txt'),
             'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir11_new (conflict copy 1)'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT),
          (('.', 'dir2_modified'),
              change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified', 'dir2_11_new'),
              change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified', 'dir2_11_new', 'test_conflict_new.txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_dir_modified_but_deleted(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Delete dir, which was modified, no conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir2_modified'))

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
          dc_final,
          [(('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified'),
              change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified', 'test2_1_unchanged.txt'),
              change_entry.CONTENT_STATUS_DELETED),
          (('.', 'dir2_modified', 'dir2_1_unchanged'),
              change_entry.CONTENT_STATUS_DELETED),
          (('.', 'dir2_modified', 'dir2_1_unchanged',
            'test2_1_1_unchanged.txt'),
              change_entry.CONTENT_STATUS_DELETED)])

  def test_change_entry_conflict_dir_modified_but_to_file(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Change the dir to file, which was modified, conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_2_modified'))
    f = open(os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_2_modified'), 'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified'),
              change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir2_modified', 'dir2_2_modified (conflict copy 1)'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_dir_deleted(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Delete the dir already, no conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir3_deleted'))

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(dc_final)

  def test_change_entry_conflict_dir_deleted_but_to_file(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Change the dir to file, which was deleted, no conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir3_deleted'))
    f = open(os.path.join(_TEST_SRC, 'dir3_deleted'), 'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir3_deleted'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_dir_deleted_but_modified(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Change the dir to file, which was deleted, no conflict
    f = open(os.path.join(_TEST_SRC, 'dir3_deleted', 'dir3_1_deleted',
                          'test3_1_1_deleted.txt'),
             'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir3_deleted'),
              change_entry.CONTENT_STATUS_NEW),
          (('.', 'dir3_deleted', 'dir3_1_deleted'),
              change_entry.CONTENT_STATUS_NEW),
          (('.', 'dir3_deleted', 'dir3_1_deleted', 'test3_1_1_deleted.txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])

  def test_change_entry_conflict_to_file_but_deleted(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Delete the dir already, no conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir10_become_file'))

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(dc_final)

  def test_change_entry_conflict_to_file_already(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Change the dir to file already, but different content, conflict
    shutil.rmtree(os.path.join(_TEST_SRC, 'dir10_become_file'))
    f = open(os.path.join(_TEST_SRC, 'dir10_become_file'), 'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()
    # Change the dir to file already, same content, no conflict
    shutil.rmtree(
        os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_10_become_file'))
    f = open(os.path.join(_TEST_SRC, 'dir2_modified', 'dir2_10_become_file'),
             'w')
    f.write('dir2_10\n')
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          # Existing file has the content already there
          (('.', 'dir10_become_file'),
              change_entry.CONTENT_STATUS_MODIFIED, _TEST_CONFLICT_CONTENT),
          # Conflict copy has the content from the sync
          (('.', 'dir10_become_file (conflict copy 1)'),
              change_entry.CONTENT_STATUS_NEW, 'dir10\n')])

  def test_change_entry_conflict_to_dir_but_modified(self):
    os.chdir(_TEST_DEST)
    di_new = file_info.load_dir_info('.', calculate_hash=True)
    os.chdir(_TEST_SRC)
    di_old = file_info.load_dir_info('.', calculate_hash=True)
    dc = change_entry.get_dir_changes(di_new, di_old, root_dir=_TEST_DEST,
                                      tmp_dir=_TEST_TMP)

    # Generate conflict
    # Modify the files in subdirectory of the dir to become file, conflict
    f = open(os.path.join(_TEST_SRC, 'dir10_become_file',
                          'test10_1_deleted.txt'),
             'w')
    f.write(_TEST_CONFLICT_CONTENT)
    f.close()

    # Apply dir changes to _TEST_SRC
    change_entry.apply_dir_changes_to_dir(_TEST_SRC, dc)

    # Verify the dir status
    os.chdir(_TEST_SRC)
    di_final = file_info.load_dir_info('.', calculate_hash=True)

    dc_final = change_entry.get_dir_changes(di_final, di_new)
    self._assertDirChanges(
        dc_final,
        special_cases=[
          (('.'), change_entry.CONTENT_STATUS_MODIFIED),
          (('.', 'dir10_become_file (conflict copy 1)'),
              change_entry.CONTENT_STATUS_NEW, 'dir10\n'),
          (('.', 'dir10_become_file'),
              change_entry.CONTENT_STATUS_TO_DIR),
          (('.', 'dir10_become_file', 'test10_1_deleted.txt'),
              change_entry.CONTENT_STATUS_NEW, _TEST_CONFLICT_CONTENT)])


