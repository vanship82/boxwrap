import inspect
import os
import shutil
import subprocess
import sys

PROGRAM_COMMON = 'boxwrap'
COMPRESSED_FILENAME_SUFFIX = '.%s.zip' % PROGRAM_COMMON

ZIP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(
        inspect.currentframe()))),
    'third_party')
ZIP_BIN = '7za'

INVALID_PASSWORD = 'INVALID_PASSWORD_DO_NOT_USE_AT_ALL_NOTICE_NOTICE_NOTICE'

ENCRYPTION_ZIP_CRYPTO = 'ZipCrypto'
ENCRYPTION_AES_128 = 'AES128'
ENCRYPTION_AES_192 = 'AES192'
ENCRYPTION_AES_256 = 'AES256'

COMPRESSION_LEVEL_NONE = 0
COMPRESSION_LEVEL_LOW = 1
COMPRESSION_LEVEL_NORMAL = 5
COMPRESSION_LEVEL_HIGH = 9


class CompressionException(Exception):
  def __init__(self, message, returncode):
    Exception.__init__(self, message)
    self.returncode = returncode
  pass


class CompressionWarning(CompressionException):
  pass


class CompressionFatalError(CompressionException):
  pass


class CompressionCommandLineError(CompressionException):
  pass


class CompressionInsufficientMemory(CompressionException):
  pass


class CompressionUserInterrupt(CompressionException):
  pass


RETURN_CODE_EXCEPTION_MAP = {
    1: CompressionWarning,
    2: CompressionFatalError,
    7: CompressionCommandLineError,
    8: CompressionInsufficientMemory,
    255: CompressionUserInterrupt}


def get_compressed_filename(filename):
  return filename + COMPRESSED_FILENAME_SUFFIX


def get_original_filename(filename):
  if is_compressed_filename(filename):
    return filename[:-len(COMPRESSED_FILENAME_SUFFIX)]
  else:
    return filename


def is_compressed_filename(filename):
  return filename.endswith(COMPRESSED_FILENAME_SUFFIX)


# @return   output filename, if success; None and exceptions otherwise.
def compress_file(src_file, dest_file,
                  compression_level=COMPRESSION_LEVEL_NORMAL,
                  password=None,
                  encryption_method=ENCRYPTION_ZIP_CRYPTO):
  params = [os.path.join(ZIP_PATH, ZIP_BIN), 'a', '-tzip', '-aoa',
            '-mx=%d' % compression_level]
  if password:
    params.append('-p%s' % password)
    params.append('-mem=%s' % encryption_method)

  params.append(os.path.abspath(dest_file))
  params.append(os.path.basename(src_file))

  try:
    cwd = os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(os.path.dirname(src_file)))
    subprocess.check_call(params, shell=False,
                          stderr=open('/dev/null'),
                          stdout=open('/dev/null'))
    os.chdir(cwd)
    shutil.copystat(src_file, dest_file)
    return dest_file
  except subprocess.CalledProcessError as e:
    if RETURN_CODE_EXCEPTION_MAP.has_key(e.returncode):
      raise RETURN_CODE_EXCEPTION_MAP[e.returncode]('', e.returncode)
    else:
      raise CompressionException('', e.returncode)

def compress_recursively(path, src_base_path, dest_base_path,
                         compression_level=COMPRESSION_LEVEL_NORMAL,
                         password=None,
                         encryption_method=ENCRYPTION_ZIP_CRYPTO):
  src_total_path = os.path.join(src_base_path, path)
  dest_total_path = os.path.join(dest_base_path, path)
  if os.path.isfile(src_total_path):
    compress_file(src_total_path,
                  get_compressed_filename(dest_total_path),
                  compression_level=compression_level,
                  password=password,
                  encryption_method=encryption_method)
    return

  if not os.path.exists(dest_total_path):
    os.makedirs(dest_total_path)

  for (cur_path, dirs, files) in os.walk(src_total_path):
    rel_path = os.path.relpath(cur_path, src_base_path)
    cur_dest_path = os.path.join(dest_base_path, rel_path)
    for d in dirs:
      os.makedirs(os.path.join(cur_dest_path, d))

    for f in files:
      compress_file(os.path.join(cur_path, f),
                    get_compressed_filename(
                        os.path.join(cur_dest_path, f)),
                    compression_level=compression_level,
                    password=password,
                    encryption_method=encryption_method)

# @return   output filename, if success; None and exceptions otherwise.
def decompress_file(src_file, dest_file,
                    password=None):
  params = [os.path.join(ZIP_PATH, ZIP_BIN), 'x', '-so']
  test_params = [os.path.join(ZIP_PATH, ZIP_BIN), 't']
  if password:
    params.append('-p%s' % password)
    test_params.append('-p%s' % password)
  else:
    params.append('-p%s' % INVALID_PASSWORD)
    test_params.append('-p%s' % INVALID_PASSWORD)

  params.append(src_file)
  test_params.append(src_file)

  try:
    subprocess.check_call(test_params, shell=False,
                          stderr=open('/dev/null'),
                          stdout=open('/dev/null'))
    dest_f = open(dest_file, 'w')
    subprocess.check_call(params, shell=False, stdout=dest_f,
                          stderr=open('/dev/null'))
    dest_f.close()
    shutil.copystat(src_file, dest_file)
    return dest_file
  except subprocess.CalledProcessError as e:
    if RETURN_CODE_EXCEPTION_MAP.has_key(e.returncode):
      raise RETURN_CODE_EXCEPTION_MAP[e.returncode]('', e.returncode)
    else:
      raise CompressionException('', e.returncode)

def decompress_recursively(path, src_base_path, dest_base_path,
                           password=None):
  src_total_path = os.path.join(src_base_path, path)
  dest_total_path = os.path.join(dest_base_path, path)
  if os.path.isfile(src_total_path):
    decompress_file(src_total_path,
                    get_original_filename(dest_total_path),
                    password=password)
    return

  if not os.path.exists(dest_total_path):
    os.makedirs(dest_total_path)

  for (cur_path, dirs, files) in os.walk(src_total_path):
    rel_path = os.path.relpath(cur_path, src_base_path)
    cur_dest_path = os.path.join(dest_base_path, rel_path)
    for d in dirs:
      os.makedirs(os.path.join(cur_dest_path, d))

    for f in files:
      decompress_file(os.path.join(cur_path, f),
                      get_original_filename(
                          os.path.join(cur_dest_path, f)),
                      password=password)

