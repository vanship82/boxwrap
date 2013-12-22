import argparse
import collections
import compression
import ConfigParser
import getpass
import os
import sys

import main
from sync import file_info


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
      '-p', dest='password', action='store_true',
      help='Supply a password, please enter after promp.')
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
  args = _parse_args()
  profile_new = False
  profile_base = os.path.abspath(os.path.expanduser(args.profile_dir))

  profile = args.profile
  profile_dir = os.path.join(profile_base, profile)
  working_dir = args.working_dir
  password = args.password
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
    if profile_info.has_option(_PROFILE_INFO_SECTION, 'password'):
      password = profile_info.getboolean(_PROFILE_INFO_SECTION, 'password')
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

  if rewrite_profile_info:
    print >>sys.stderr, 'Save to profile info file: %s' % (
        os.path.join(profile_dir, _PROFILE_INFO_FILE))
    new_profile_info = ConfigParser.RawConfigParser()
    new_profile_info.add_section(_PROFILE_INFO_SECTION)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'profile', profile)
    new_profile_info.set(
        _PROFILE_INFO_SECTION, 'working_dir', working_dir)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'wrap_dir', wrap_dir)
    new_profile_info.set(_PROFILE_INFO_SECTION, 'password', password)
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


def _boxwrap():
  args = _validate_args_and_update_profile(_parse_args())
  password = None
  if args['password']:
    password = getpass.getpass(
        'Please enter password for encrypting/decrypting wrap_dir:')
  boxwrap = main.BoxWrap(
      args['working_dir'], args['wrap_dir'],
      os.path.join(args['profile_dir'], _PROFILE_TMP_DIR),
      os.path.join(args['profile_dir'], _PROFILE_DIR_INFO_FILE),
      password=password,
      encryption_method=_ENCRYPTION_CHOICES[args['encryption_method']],
      compression_level=_COMPRESSION_CHOICES[args['compression_level']])
  boxwrap.sync(file_info.empty_dir_info('.'), debug=True)


if __name__ == '__main__':
  _boxwrap()

