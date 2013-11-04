import csv
import glob
import hashlib
import os
import traceback

import cStringIO

from util import i18n
from util import util


class FileEntry:

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


def load_file_entry(path):
  if not os.path.exists(path):
    return None
  try:
    stat = os.stat(path)
    is_dir = os.path.isdir(path)
    return FileEntry(
        path,
        is_dir,
        stat.st_mode,
        stat.st_size if not is_dir else None,
        stat.st_mtime)
  except:
    return None


def load_from_csv_row(row):
  return FileEntry(
      row[0],
      row[1] == '1',
      int(row[2]),
      int(row[3]) if int(row[3]) >= 0 else None,
      float(row[4]),
      row[5] or None)


def load_csv(f):
  reader = i18n.UnicodeReader(f)
  result = []
  for row in reader:
    if len(row) < 6:
      continue
    result.append(load_from_csv_row(row))
  return result


def load_dir_recursively(dir_path):
  file_entries = []
  for root, dirs, files in os.walk(dir_path):
    file_entries.append(load_file_entry(root))
    for f in files:
      file_entries.append(load_file_entry(os.path.join(root, f)))
  file_entries.sort(
      key=lambda file_entry: file_entry.path_for_sorting())
  return file_entries


def write_sorted_list_to_csv(sorted_file_entry_list, f):
  for entry in sorted_file_entry_list:
    entry.calculate_hash()
    f.write(entry.to_csv())
    f.write('\n')


