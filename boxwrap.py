import argparse
import collections
import compression
import ConfigParser
import getpass
import hashlib
import os
import shutil
import sys

import main
from sync import file_info


# Maximum rounds of sync from a single round. We may need two or more rounds
# if there are conflicts, dir/file transition, or continuously changing
# content.
_MAX_ROUND_SYNC=5

_PROFILE_INFO_FILE='profile.ini'
_PROFILE_DIR_INFO_FILE='profile_dir.csv'
_PROFILE_TMP_DIR='tmp'

_PROFILE_INFO_SECTION='BoxWrap'

_ENCRYPTION_CHOICES=collections.OrderedDict([
    ('zipcrypto', compression.ENCRYPTION_ZIP_CRYPTO),
    ('aes128', compression.ENCRYPTION_AES_128),
    ('aes192', compression.ENCRYPTION_AES_192),
    ('aes256', compression.ENCRYPTION_AES_256)])
_COMPRESSION_CHOICES=collections.OrderedDict([
    ('none', compression.COMPRESSION_LEVEL_NONE),
    ('low', compression.COMPRESSION_LEVEL_LOW),
    ('normal', compression.COMPRESSION_LEVEL_NORMAL),
    ('high', compression.COMPRESSION_LEVEL_HIGH)])


def _parse_args():
  parser = argparse.ArgumentParser(
      description='BoxWrap: store your files to cloud in a secure and compressed way.')
  parser.add_argument(
      'profile', metavar='profile', type=str,
      help='Profile name to store sync/merge metadata in profile directory.')
  parser.add_argument(
      'working_dir', metavar='working_dir', type=str, nargs='?',
      help='Optional. Local working directory with decrypted and uncompressed files. Not required if the profile already exists.')
  parser.add_argument(
      'wrap_dir', metavar='wrap_dir', type=str, nargs='?',
      help='Optional. Wrap directory with encrypted and compressed files, usually pointing to one of your cloud subdirectory. Not required if the profile already exists.')
  parser.add_argument(
      '--profile_dir', metavar='profile_dir', type=str,
      default=os.path.join('~', '.boxwrap'),
      help='Profile directory to store sync/merge metadata.[default=%s]' % os.path.join('~', '.boxwrap'))
  parser.add_argument(
      '-p', dest='require_password', action='store_true',
      help='Supply a password, please enter after promp.')
  parser.add_argument(
      '--force_new_password', dest='force_new_password', action='store_true',
      help='Force using new password regardless to the hash saved in profile.')
  parser.add_argument(
      '-l', dest='compression_level',
      default='normal',
      choices=_COMPRESSION_CHOICES.keys(),
      help='Compression level to be speficied to 7-zip.[default=normal]')
  parser.add_argument(
      '-m', dest='encryption_method',
      default='zipcrypto',
      choices=_ENCRYPTION_CHOICES.keys(),
      help='Encryption method to be speficied to 7-zip. Zipcrypto has most compatability but less secure.[default=zipcrypto]')
  return parser.parse_args()


def _require_working_and_wrap_dir(profile, working_dir, wrap_dir):
  if not working_dir or not wrap_dir:
    print >>sys.stderr, 'Error:'
    if not working_dir:
      print >>sys.stderr, (
          'working_dir is required for new profile %s' % profile)
    if not wrap_dir:
      print >>sys.stderr, (
          'wrap_dir is required for new profile %s' % profile)
    sys.exit()


def _require_working_and_wrap_dir_exists(profile, working_dir, wrap_dir):
  if not os.path.isdir(working_dir) or not os.path.isdir(wrap_dir):
    print >>sys.stderr, 'Error:'
    if not os.path.isdir(working_dir):
      print >>sys.stderr, (
          'working_dir %s should be an existing directory for profile %s' %
          (working_dir, profile))
    if not os.path.isdir(wrap_dir):
      print >>sys.stderr, (
          'wrap_dir %s should be an existing directory for profile %s' %
          (wrap_dir, profile))
    sys.exit()


def _validate_args_and_update_profile(args):
  profile_new = False
  profile_base = os.path.abspath(os.path.expanduser(args.profile_dir))

  profile = args.profile
  profile_dir = os.path.join(profile_base, profile)
  working_dir = args.working_dir
  require_password = args.require_password
  password_hash = None
  password = None
  force_new_password = args.force_new_password
  encryption_method = args.encryption_method
  compression_level = args.compression_level

  wrap_dir = args.wrap_dir
  if os.path.isfile(profile_dir):
    print >>sys.stderr, 'Error:'
    print >>sys.stderr, (
        'Destination profile location %s is not a directory' % profile_dir)
    sys.exit()
  if not os.path.exists(profile_dir):
    profile_new = True
    _require_working_and_wrap_dir(profile, working_dir, wrap_dir)
    try:
      os.makedirs(profile_dir)
    except:
      print >>sys.stderr, 'Error:'
      print >>sys.stderr, ('Cannot create directory for profile %s at %s' %
          (profile, profile_dir))
      sys.exit()
  if os.path.isdir(os.path.join(profile_dir, _PROFILE_INFO_FILE)):
    print >>sys.stderr, 'Error:'
    print >>sys.stderr, ('Destination profile info file %s is not a file' %
        os.path.join(profile_dir, _PROFILE_INFO_FILE))
    sys.exit()
  if not os.path.exists(os.path.join(profile_dir, _PROFILE_INFO_FILE)):
    print >>sys.stderr, 'Create new profile %s' % profile
    profile_new = True
    _require_working_and_wrap_dir(profile, working_dir, wrap_dir)
  rewrite_profile_info = True
  if not profile_new:
    print >>sys.stderr, 'Load existing profile %s' % profile
    print >>sys.stderr, 'Note that the existing profile fields will be used instead of the supplied arguments.'
    # Normally we don't rewrite profile info unless there are some missing
    # fields.
    rewrite_profile_info = False
    profile_info = ConfigParser.ConfigParser()
    profile_info.read(os.path.join(profile_dir, _PROFILE_INFO_FILE))
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'working_dir'):
      working_dir = profile_info.get(_PROFILE_INFO_SECTION, 'working_dir')
    else:
      rewrite_profile_info = True
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'wrap_dir'):
      wrap_dir = profile_info.get(_PROFILE_INFO_SECTION, 'wrap_dir')
    else:
      rewrite_profile_info = True
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'require_password'):
      require_password = profile_info.getboolean(_PROFILE_INFO_SECTION,
                                                 'require_password')
      if require_password:
        if profile_info.has_option(_PROFILE_INFO_SECTION, 'password_hash'):
          password_hash = profile_info.get(_PROFILE_INFO_SECTION,
                                           'password_hash')
    else:
      rewrite_profile_info = True
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'encryption_method'):
      encryption_method2 = profile_info.get(_PROFILE_INFO_SECTION,
                                            'encryption_method')
      if encryption_method2 in _ENCRYPTION_CHOICES:
        encryption_method = encryption_method2
      else:
        rewrite_profile_info = True
    else:
      rewrite_profile_info = True
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'compression_level'):
      compression_level2 = profile_info.get(_PROFILE_INFO_SECTION,
                                            'compression_level')
      if compression_level2 in _COMPRESSION_CHOICES:
        compression_level = compression_level2
      else:
        rewrite_profile_info = True
    else:
      rewrite_profile_info = True

  working_dir = os.path.abspath(working_dir)
  wrap_dir = os.path.abspath(wrap_dir)
  _require_working_and_wrap_dir_exists(profile, working_dir, wrap_dir)

  if require_password or force_new_password:
    require_password = True
    while True:
      password = getpass.getpass(
          'Please enter password for encrypting/decrypting wrap_dir:',
          stream=sys.stderr)
      if force_new_password or not password_hash:
        if force_new_password:
          print >>sys.stderr, 'Warning: force new password flag is set, you may get an inconsistent encryption password in wrap_dir.'
        confirm_password = getpass.getpass(
            'Please confirm your password:', stream=sys.stderr)
        if confirm_password != password:
          print >>sys.stderr, 'Password confirmation does not match, please re-enter.'
          continue
        rewrite_profile_info = True
      else:
        if _calculate_password_hash(password, profile) != password_hash:
          print >>sys.stderr, 'Password does not match to profile, please re-enter.'
          continue
      break

  if rewrite_profile_info:
    print >>sys.stderr, 'Save to profile info file: %s' % (
        os.path.join(profile_dir, _PROFILE_INFO_FILE))
    new_profile_info = ConfigParser.RawConfigParser()
    new_profile_info.add_section(_PROFILE_INFO_SECTION)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'profile', profile)
    new_profile_info.set(
        _PROFILE_INFO_SECTION, 'working_dir', working_dir)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'wrap_dir', wrap_dir)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'require_password',
                         require_password)
    if require_password:
      new_profile_info.set(_PROFILE_INFO_SECTION, 'password_hash',
                           _calculate_password_hash(password, profile))
    new_profile_info.set(
        _PROFILE_INFO_SECTION, 'encryption_method', encryption_method)
    new_profile_info.set(
        _PROFILE_INFO_SECTION, 'compression_level', compression_level)
    with open(os.path.join(profile_dir, _PROFILE_INFO_FILE), 'wb') as f:
        new_profile_info.write(f)

  if os.path.isfile(os.path.join(profile_dir, _PROFILE_TMP_DIR)):
    os.remove(os.path.join(profile_dir, _PROFILE_TMP_DIR))
  if not os.path.exists(os.path.join(profile_dir, _PROFILE_TMP_DIR)):
    os.makedirs(os.path.join(profile_dir, _PROFILE_TMP_DIR))
  return {
      'profile': profile,
      'profile_base': profile_base,
      'profile_dir': profile_dir,
      'working_dir': working_dir,
      'wrap_dir': wrap_dir,
      'password': password,
      'encryption_method': encryption_method,
      'compression_level': compression_level}


def _calculate_password_hash(password, profile):
  sha256 = hashlib.sha256()
  sha256.update(profile + compression.PROGRAM_COMMON + password)
  return sha256.hexdigest()


def _clean_up_tmp_dir(profile_dir):
  profile_tmp_dir = os.path.join(profile_dir, _PROFILE_TMP_DIR)
  map(os.unlink,
      [os.path.join(profile_tmp_dir,f) for f in os.listdir(profile_tmp_dir)])


def _human_readable_size(size):
  if size >= 1024 * 1024 * 1024:
    return '%.2fGB' % (size / (1024 * 1024 * 1024.0))
  elif size >= 1024 * 1024:
    return '%.2fMB' % (size / (1024 * 1024.0))
  elif size >= 1024:
    return '%.2fKB' % (size / 1024.0)
  else:
    return '%s' % size


def _boxwrap():
  args = _validate_args_and_update_profile(_parse_args())
  password = args['password']
  profile_dir_info_file = os.path.join(
      args['profile_dir'], _PROFILE_DIR_INFO_FILE)
  _clean_up_tmp_dir(args['profile_dir'])
  if os.path.isdir(profile_dir_info_file):
    shutil.rmtree(profile_dir_info_file)
  if os.path.isfile(profile_dir_info_file):
    dir_info = file_info.load_dir_info_from_csv(
        open(profile_dir_info_file), '.')
  else:
    dir_info = file_info.empty_dir_info('.')
  try:
    boxwrap = main.BoxWrap(
        args['working_dir'], args['wrap_dir'],
        os.path.join(args['profile_dir'], _PROFILE_TMP_DIR),
        profile_dir_info_file,
        password=password,
        encryption_method=_ENCRYPTION_CHOICES[args['encryption_method']],
        compression_level=_COMPRESSION_CHOICES[args['compression_level']])
    for i in range(_MAX_ROUND_SYNC):
      print >>sys.stderr, 'Performing sync and merge round #%s' % (i + 1)
      has_changes, working_di, wrap_di = boxwrap.sync(dir_info, verbose=True)
      if not has_changes:
        break
      with open(profile_dir_info_file, 'wb') as f:
        working_di.write_to_csv(f)
      dir_info = working_di

    working_size = 0
    for fi in working_di.flat_file_info_list():
      if not fi.is_dir:
        working_size += fi.size
    wrap_size = 0
    for fi in wrap_di.flat_file_info_list():
      if not fi.is_dir:
        wrap_size += fi.compressed_file_info.size

    print 'Working dir size: %s' % _human_readable_size(working_size)
    print 'Wrap dir size: %s' % _human_readable_size(wrap_size)
    print 'Save space: %.2g%%' % (
        (working_size - wrap_size) * 100.0 / working_size)

    if has_changes:
      print 'Sync is incomplete, you may run again to complete sync.'
    else:
      print 'No changes are found. Sync is completed.'
  except compression.CompressionException as e:
    print >>sys.stderr, (
        '%s. The archive %s is not able to be decompressed.' %
        e.get_message(), e.path)
  finally:
    _clean_up_tmp_dir(args['profile_dir'])


if __name__ == '__main__':
  _boxwrap()

