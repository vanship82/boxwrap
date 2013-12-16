import csv
import glob
import hashlib
import os
import shutil
import traceback

import cStringIO

from util import i18n
from util import util


class FileInfo:

  def __init__(
      self, path, is_dir, mode, size, last_modified_time, file_hash=None,
      tmp_file=None, compressed_file_info=None, original_file_info=None):
    self.path = path
    self.is_dir = is_dir
    self.mode = mode
    self.size = size
    self.last_modified_time = last_modified_time
    self.file_hash = file_hash
    self.tmp_file = tmp_file
    self.compressed_file_info = compressed_file_info
    self.original_file_info = original_file_info

  def copy(self, other):
    self.path = other.path
    self.is_dir = other.is_dir
    self.mode = other.mode
    self.size = other.size
    self.last_modified_time = other.last_modified_time
    self.file_hash = other.file_hash
    self.tmp_file = other.tmp_file
    self.compressed_file_info = other.compressed_file_info
    self.original_file_info = other.original_file_info

  def calculate_hash(self, overwrite=False):
    if self.is_dir:
      return None
    if not overwrite and self.file_hash:
      return self.file_hash
    self.file_hash = _calculate_hash(self.path)
    return self.file_hash

  def path_for_sorting(self):
    return util.path_for_sorting(self.path)

  def to_csv(self):
    output = cStringIO.StringIO()
    writer = i18n.UnicodeWriter(output)
    writer.writerow([
      self.path,
      '1' if self.is_dir else '0',
      str(self.mode),
      str(self.size) if self.size is not None else '-1',
      str(self.last_modified_time),
      str(self.file_hash) if self.file_hash else ''])
    return output.getvalue().strip('\r\n')

  def is_modified(self, other, force_check_content=False):
    if self.is_dir != other.is_dir:
      return True
    if self.is_dir:
      return False
    if self.file_hash and other.file_hash:
      return self.file_hash != other.file_hash
    if (not force_check_content and self.size == other.size and
        self.last_modified_time == other.last_modified_time):
      return False
    elif (self.size != other.size or
        self.calculate_hash() != other.calculate_hash()):
      return True
    return False

  def copy_tmp(self, dest_path):
    if not self.tmp_file:
      raise Exception("Error copy empty tmp file: %s" % self)
    shutil.copy2(self.tmp_file, dest_path)

  def __str__(self):
    return (
        'path: %s, is_dir: %s, mode: 0%o size: %s, last_modified_time: %s, '
        'file_hash: %s, tmp_file: %s%s%s' % (
            self.path,
            self.is_dir,
            self.mode,
            self.size,
            self.last_modified_time,
            self.file_hash,
            self.tmp_file,
            ('\n    compressed_file_info: %s' % self.compressed_file_info
                if self.compressed_file_info else ''),
            ('\n    original_file_info: %s' % self.original_file_info
                if self.original_file_info else '')))


def _calculate_hash(path):
  sha1 = hashlib.sha1()
  f = open(path, 'rb')
  try:
    sha1.update(f.read())
  finally:
    f.close()
  return sha1.hexdigest()


def copy_with_tmp_file(file_info, tmp_file, tmp_dir):
  # When tmp_file is available, always calculate its hash
  file_hash=file_info.file_hash
  full_tmp_path = os.path.join(tmp_dir, tmp_file)
  if not file_hash and tmp_file:
    file_hash = _calculate_hash(full_tmp_path)
  return FileInfo(file_info.path, file_info.is_dir, file_info.mode,
                  file_info.size, file_info.last_modified_time,
                  file_hash=file_hash, tmp_file=full_tmp_path)


def load_file_info(path, calculate_hash=False):
  if not os.path.exists(path):
    return None
  try:
    stat = os.stat(path)
    is_dir = os.path.isdir(path)
    file_hash = _calculate_hash(path) if calculate_hash and not is_dir else None
    return FileInfo(
        path,
        is_dir,
        stat.st_mode,
        stat.st_size if not is_dir else None,
        stat.st_mtime,
        file_hash=file_hash)
  except:
    return None


def load_from_csv_row(row):
  return FileInfo(
      row[0],
      row[1] == '1',
      int(row[2]),
      int(row[3]) if int(row[3]) >= 0 else None,
      float(row[4]),
      row[5] or None)


# A sorted list of file info in the directory
class DirInfo:

  def __init__(self, base_dir, file_info_list, dir_info_dict, key=None):
    self._file_info_list = _sort_file_info_list(list(file_info_list), key=key)
    self._fi_dict = {(x.path, x) for x in self._file_info_list}
    self._dir_info_dict = dir_info_dict
    self._base_dir = base_dir

  def base_dir(self):
    return self._base_dir

  def file_info_list(self):
    return self._file_info_list

  def dir_info(self, dir_path):
    return self._dir_info_dict[dir_path]

  def flat_file_info_list(self):
    for fi in self._file_info_list:
      yield fi
      if (fi.is_dir and fi.path in self._dir_info_dict
          and self._dir_info_dict[fi.path]):
        for sub_fi in self._dir_info_dict[fi.path].flat_file_info_list():
          yield sub_fi

  def has_file(self, path):
    fi = self._fi_dict[path]
    relpath = os.path.relpath(pth, self._base_dir)
    if '..' in relpath:
      return False
    relpath_split = relpath.split(os.sep)
    if len(relpath_split) == 1:
      return path in self._fi_dict
    else:
      next_base = os.path.join(self._base_dir, relpath_split[0])
      if next_base in self._dir_info_dict:
        return self._dir_info_dict[next_base].has_file(path)
      else:
        return False

  def get(self, path):
    fi = self._fi_dict[path]
    relpath = os.path.relpath(pth, self._base_dir)
    if '..' in relpath:
      return None
    relpath_split = relpath.split(os.sep)
    if len(relpath_split) == 1:
      return self._fi_dict.get(path)
    else:
      next_base = os.path.join(self._base_dir, relpath_split[0])
      if next_base in self._dir_info_dict:
        return self._dir_info_dict[next_base].get(path)
      else:
        return None

  def write_to_csv(self, f):
    for entry in self.flat_file_info_list():
      entry.calculate_hash()
      f.write(entry.to_csv())
      f.write('\n')


def _sort_file_info_list(file_info_list, key=None):
  if not key:
    key=lambda file_info: file_info.path_for_sorting()
  file_info_list.sort(key=key)
  return file_info_list


def load_dir_info_from_csv(f, base_dir, key=None):
  reader = i18n.UnicodeReader(f)
  file_info_list = []
  for row in reader:
    if len(row) < 6:
      continue
    file_info_list.append(load_from_csv_row(row))
  dir_info, unused = _sorted_file_info_list_to_dir_info(
      base_dir, file_info_list, 0, key=key)
  return dir_info


# recursively
def load_dir_info(dir_path, calculate_hash=False, key=None):
  file_info_list = []
  for root, dirs, files in os.walk(dir_path):
    file_info_list.append(load_file_info(root))
    for f in files:
      file_info_list.append(load_file_info(os.path.join(root, f),
                            calculate_hash=calculate_hash))
  dir_info, unused = _sorted_file_info_list_to_dir_info(
      dir_path, file_info_list, 0, key=key)
  return dir_info


# Load as relative path
def load_rel_dir_info(dir_path, key=None):
  old_cwd = os.getcwd()
  os.chdir(dir_path)
  dir_info = load_dir_info('.', key=None)
  os.chdir(old_cwd)
  return dir_info


def load_dir_info_from_file_info_list(base_dir, file_info_list, key=None):
  dir_info, unused = _sorted_file_info_list_to_dir_info(
      base_dir, _sort_file_info_list(file_info_list, key=key), 0)
  return dir_info


def empty_dir_info(dir_path):
  stat = os.stat(dir_path)
  return DirInfo(
      dir_path,
      [FileInfo(dir_path, True, stat.st_mode, None, stat.st_mtime)],
      {dir_path: None})


def _sorted_file_info_list_to_dir_info(
    base, sorted_file_info_list, start_index, key=None):
  i = start_index
  base_file_info_list = []
  base_dir_info_dict = {}
  while i < len(sorted_file_info_list):
    fi = sorted_file_info_list[i]
    if '..' in os.path.relpath(fi.path, base):
      break
    if fi.is_dir:
      base_file_info_list.append(fi)
      dir_info, i = _sorted_file_info_list_to_dir_info(
          fi.path, sorted_file_info_list, i + 1)
      base_dir_info_dict[fi.path] = dir_info
    else:
      base_file_info_list.append(fi)
    i += 1
  return DirInfo(base, base_file_info_list, base_dir_info_dict, key=key), i - 1

