import compression
import filecmp
import inspect
import os
import shutil
import unittest

_CASE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
    os.path.join('cases', 'compression'))
_CASE_SRC = os.path.join(_CASE_BASE_DIR, 'src')
_CASE_DEST = os.path.join(_CASE_BASE_DIR, 'dest')
_CASE_OUT = os.path.join(_CASE_BASE_DIR, 'out')
_CASE_TMP = os.path.join(_CASE_BASE_DIR, 'tmp')
_CASE_PATH = 'dir'

class TestCompressionCases(unittest.TestCase):

  def setUp(self):
    if os.path.exists(_CASE_SRC):
      shutil.rmtree(_CASE_SRC)
    if os.path.exists(_CASE_DEST):
      shutil.rmtree(_CASE_DEST)
    if os.path.exists(_CASE_OUT):
      shutil.rmtree(_CASE_OUT)
    if os.path.exists(_CASE_TMP):
      shutil.rmtree(_CASE_TMP)
    os.makedirs(_CASE_SRC)
    os.makedirs(_CASE_DEST)
    os.makedirs(_CASE_OUT)
    os.makedirs(_CASE_TMP)
    path = os.path.join(_CASE_SRC, _CASE_PATH)
    os.makedirs(path)
    f = open(os.path.join(path, 'test.txt'), 'w')
    f.write('test123')
    f.close()
    os.makedirs(os.path.join(path, 'testdir'))
    f = open(os.path.join(path, os.path.join('testdir', 'test_in_dir.txt')),
             'w')
    f.write('test123_in_dir')
    f.close()

  def test_copmression(self):
    compression.compress_recursively(
        _CASE_PATH, _CASE_SRC, _CASE_DEST, password=None,
        encryption_method=compression.ENCRYPTION_AES_256)
    src = os.path.join(_CASE_SRC, _CASE_PATH)
    dest = os.path.join(_CASE_DEST, _CASE_PATH)
    for path, dirs, files in os.walk(src):
      rel_path = os.path.relpath(path, src)
      dest_path = os.path.join(dest, rel_path)
      for f in files:
        self.assertTrue(
            'Compressed file %s is not found for %s' % (
                os.path.join(dest_path,
                    compression.get_compressed_filename(f)),
                os.path.join(path, f)),
            os.path.exists(os.path.join(dest_path,
                compression.get_compressed_filename(f))))

  def test_decopmression(self):
    compression.compress_recursively(
        _CASE_PATH, _CASE_SRC, _CASE_DEST, password=None,
        encryption_method=compression.ENCRYPTION_AES_256)
    compression.decompress_recursively(
        _CASE_PATH, _CASE_DEST, _CASE_OUT, _CASE_TMP, password=None)
    src = os.path.join(_CASE_SRC, _CASE_PATH)
    out = os.path.join(_CASE_OUT, _CASE_PATH)
    for path, dirs, files in os.walk(src):
      rel_path = os.path.relpath(path, src)
      out_path = os.path.join(out, rel_path)
      for f in files:
        self.assertTrue(
            'Decompressed file %s is not found for %s' % (
                os.path.join(out_path, f),
                os.path.join(path, f)),
            os.path.exists(os.path.join(out_path, f)))
        self.assertTrue(
            'Decompressed file %s is not identical to %s' % (
                os.path.join(out_path, f),
                os.path.join(path, f)),
            filecmp.cmp(os.path.join(path, f), os.path.join(out_path, f)))

  def test_decopmression_correct_password(self):
    compression.compress_recursively(
        _CASE_PATH, _CASE_SRC, _CASE_DEST, password='123456',
        encryption_method=compression.ENCRYPTION_AES_256)
    compression.decompress_recursively(
        _CASE_PATH, _CASE_DEST, _CASE_OUT, _CASE_TMP, password='123456')
    src = os.path.join(_CASE_SRC, _CASE_PATH)
    out = os.path.join(_CASE_OUT, _CASE_PATH)
    for path, dirs, files in os.walk(src):
      rel_path = os.path.relpath(path, src)
      out_path = os.path.join(out, rel_path)
      for f in files:
        self.assertTrue(
            'Decompressed file %s is not found for %s' % (
                os.path.join(out_path, f),
                os.path.join(path, f)),
            os.path.exists(os.path.join(out_path, f)))
        self.assertTrue(
            'Decompressed file %s is not identical to %s' % (
                os.path.join(out_path, f),
                os.path.join(path, f)),
            filecmp.cmp(os.path.join(path, f), os.path.join(out_path, f)))

  def test_decopmression_wrong_password(self):
    compression.compress_recursively(
        _CASE_PATH, _CASE_SRC, _CASE_DEST, password='123456',
        encryption_method=compression.ENCRYPTION_AES_256)
    # Wrong password
    self.assertRaises(
        compression.CompressionWrongPassword,
        compression.decompress_recursively,
        _CASE_PATH, _CASE_DEST, _CASE_OUT, _CASE_TMP,
        password='1234567')

  def test_decopmression_invalid_archive(self):
    # Invalid archive because we decompress src directly.
    self.assertRaises(
        compression.CompressionInvalidArchive,
        compression.decompress_recursively,
        _CASE_PATH, _CASE_SRC, _CASE_OUT, _CASE_TMP,
        password='1234567')

