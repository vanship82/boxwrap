import inspect
import os
import platform
import shutil
import subprocess
import sys

PROGRAM_COMMON = 'boxwrap'
COMPRESSED_FILENAME_SUFFIX = '.%s.zip' % PROGRAM_COMMON

ZIP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(inspect.getfile(
        inspect.currentframe()))),
    'third_party')


def _get_binary():
  arch = platform.architecture()
  binary = None
  if arch[1] == 'ELF':
    # Linux
    if arch[0] == '32bit':
      binary = '7za_linux_x86'
    elif arch[0] == '64bit':
      binary = '7za_linux_x64'
  elif arch[1] == 'WindowsPE':
    # Windows
    if arch[0] == '32bit':
      binary = os.path.join('7z_win32', '7z.exe')
    elif arch[0] == '64bit':
      binary = os.path.join('7z_win64', '7z.exe')
  if not binary:
    raise Exception('Unable to identity 7-zip binary from platform.')
  return binary


ZIP_BIN = _get_binary()

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
  def __init__(self, returncode, path, output=None):
    self.returncode = returncode
    self.path = path
    self.output = output

  def get_message(self):
    return 'Exception'


class CompressionWarning(CompressionException):
  def get_message(self):
    return 'Warning'


class CompressionFatalError(CompressionException):
  def get_message(self):
    return 'Fatal error'


class CompressionCommandLineError(CompressionException):
  def get_message(self):
    return 'Command line error'


class CompressionInsufficientMemory(CompressionException):
  def get_message(self):
    return 'Insufficient memory'


class CompressionUserInterrupt(CompressionException):
  def get_message(self):
    return 'User interrupt'


class CompressionWrongPassword(CompressionException):
  def get_message(self):
    return 'Wrong password'


class CompressionInvalidArchive(CompressionException):
  def get_message(self):
    return 'Invalid archive'


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


def generate_conflict_copy_path(path, count):
  path2 = get_original_filename(path)
  dirname, basename = os.path.split(path2)
  splits = basename.split('.')
  if len(splits) > 1:
    path3 = os.path.join(
        dirname,
        '.'.join(splits[:-1]) + ' (conflict copy %s).%s' % (count , splits[-1]))
  else:
    path3 = os.path.join(dirname, basename + ' (conflict copy %s)' %  count)
  if is_compressed_filename(path):
    return get_compressed_filename(path3)
  else:
    return path3


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

  abs_dest_file = os.path.abspath(dest_file)
  params.append(abs_dest_file)
  params.append(os.path.basename(src_file))

  try:
    cwd = os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(os.path.dirname(src_file)))
    subprocess.check_call(params, shell=False,
                          stderr=open(os.devnull),
                          stdout=open(os.devnull))
    # Hack: 7za always add .zip subfix, remove it
    if (not abs_dest_file.endswith('.zip') and
        os.path.exists(abs_dest_file + '.zip')):
      os.rename(abs_dest_file + '.zip', abs_dest_file)
    os.chdir(cwd)
    shutil.copystat(src_file, dest_file)
    return dest_file
  except subprocess.CalledProcessError as e:
    if RETURN_CODE_EXCEPTION_MAP.has_key(e.returncode):
      raise RETURN_CODE_EXCEPTION_MAP[e.returncode](e.returncode, src_file)
    else:
      raise CompressionException(e.returncode, src_file)

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

  test_process = subprocess.Popen(test_params, shell=False,
                                  stderr=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
  test_output, test_output_error = test_process.communicate()
  if test_process.returncode != 0:
    returncode = test_process.returncode
    if 'Can not open file as archive' in test_output:
      raise CompressionInvalidArchive(returncode, src_file, output=test_output)
    elif 'Wrong password?' in test_output:
      raise CompressionWrongPassword(returncode, src_file, output=test_output)
    elif RETURN_CODE_EXCEPTION_MAP.has_key(returncode, src_file):
      raise RETURN_CODE_EXCEPTION_MAP[returncode](returncode, src_file,
                                                  output=test_output)
    else:
      raise CompressionException(test_output, returncode, src_file)

  try:
    dest_f = open(dest_file, 'w')
    subprocess.check_call(params, shell=False, stdout=dest_f,
                          stderr=open(os.devnull))
    dest_f.close()
    shutil.copystat(src_file, dest_file)
    return dest_file
  except subprocess.CalledProcessError as e:
    if RETURN_CODE_EXCEPTION_MAP.has_key(e.returncode):
      raise RETURN_CODE_EXCEPTION_MAP[e.returncode](e.returncode)
    else:
      raise CompressionException(e.returncode)

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

def test_decompress_file(src_file, password=None):
  test_params = [os.path.join(ZIP_PATH, ZIP_BIN), 't']
  if password:
    test_params.append('-p%s' % password)
  else:
    test_params.append('-p%s' % INVALID_PASSWORD)

  test_params.append(src_file)

  try:
    subprocess.check_call(test_params, shell=False,
                          stderr=open(os.devnull),
                          stdout=open(os.devnull))
    return True
  except subprocess.CalledProcessError as e:
    if RETURN_CODE_EXCEPTION_MAP.has_key(e.returncode):
      raise RETURN_CODE_EXCEPTION_MAP[e.returncode](e.returncode)
    else:
      raise CompressionException(e.returncode)

def test_decompress_recursively(path, src_base_path, password=None):
  src_total_path = os.path.join(src_base_path, path)
  error_list = []
  if os.path.isfile(src_total_path):
    try:
      test_decompress_file(src_total_path,
                           password=password)
    except CompressionException as e:
      if isinstance(e, CompressionFatalError):
        error_list.append(path)

    return error_list

  for (cur_path, dirs, files) in os.walk(src_total_path):
    rel_path = os.path.relpath(cur_path, src_base_path)

    for f in files:
      try:
        test_decompress_file(os.path.join(cur_path, f),
                             password=password)
      except CompressionException as e:
        if isinstance(e, CompressionFatalError):
          error_list.append(os.path.join(rel_path, f))

  return error_list

