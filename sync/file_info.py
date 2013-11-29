import csv
import glob
import hashlib
import os
import traceback

import cStringIO

from util import i18n
from util import util


class FileInfo:

  def __init__(
      self, path, is_dir, mode, size, last_modified_time, file_hash=None):
    self.path = path
    self.is_dir = is_dir
    self.mode = mode
    self.size = size
    self.last_modified_time = last_modified_time
    self.file_hash = file_hash

  def calculate_hash(self, overwrite=False):
    if self.is_dir:
      return None
    if not overwrite and self.file_hash:
      return self.file_hash
    sha1 = hashlib.sha1()
    f = open(self.path, 'rb')
    try:
      sha1.update(f.read())
    finally:
      f.close()
    self.file_hash = sha1.hexdigest()
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

  def is_modified(self, other):
    if self.is_dir != other.is_dir:
      return True
    if self.is_dir:
      return False
    if (self.size == other.size and
        self.last_modified_time == other.last_modified_time):
      return False
    elif (self.size != other.size or
        self.calculate_hash() != other.calculate_hash()):
      return True
    return False

  def __str__(self):
    return (
        'path: %s, is_dir: %s, mode: 0%o size: %s, last_modified_time: %s, '
        'file_hash: %s' % (
            self.path,
            self.is_dir,
            self.mode,
            self.size,
            self.last_modified_time,
            self.file_hash))


def load_file_info(path):
  if not os.path.exists(path):
    return None
  try:
    stat = os.stat(path)
    is_dir = os.path.isdir(path)
    return FileInfo(
        path,
        is_dir,
        stat.st_mode,
        stat.st_size if not is_dir else None,
        stat.st_mtime)
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

  def __init__(self, base_dir, file_info_list, dir_info_dict):
    self._file_info_list = _sort_file_info_list(list(file_info_list))
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
      if fi.is_dir:
        for sub_fi in self._dir_info_dict[fi.path].flat_file_info_list():
          yield fi

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


def _sort_file_info_list(file_info_list):
  file_info_list.sort(
      key=lambda file_info: file_info.path_for_sorting())
  return file_info_list


def load_dir_info_from_csv(f, base_dir):
  reader = i18n.UnicodeReader(f)
  file_info_list = []
  for row in reader:
    if len(row) < 6:
      continue
    file_info_list.append(load_from_csv_row(row))
  dir_info, unused = _sorted_file_info_list_to_dir_info(
      base_dir, file_info_list, 0)
  return dir_info


# recursively
def load_dir_info(dir_path):
  file_info_list = []
  for root, dirs, files in os.walk(dir_path):
    file_info_list.append(load_file_info(root))
    for f in files:
      file_info_list.append(load_file_info(os.path.join(root, f)))
  dir_info, unused = _sorted_file_info_list_to_dir_info(
      dir_path, file_info_list, 0)
  return dir_info


def empty_dir_info(dir_path):
  return DirInfo(dir_path, [])


def _sorted_file_info_list_to_dir_info(
    base, sorted_file_info_list, start_index):
  i = start_index
  base_file_info_list = []
  base_dir_info_dict = {}
  while i < len(sorted_file_info_list):
    fi = sorted_file_info_list[i]
    if '..' in os.path.relpath(base, fi.path):
      break
    if fi.is_dir:
      base_file_info_list.append(fi)
      dir_info, i = _sorted_file_info_list_to_dir_info(
          fi.path, sorted_file_info_list, i + 1)
      base_dir_info_dict[fi.path] = dir_info
    else:
      base_file_info_list.append(fi)
    i += 1
  return DirInfo(base, base_file_info_list, base_dir_info_dict), i - 1


  return False
  dasda


