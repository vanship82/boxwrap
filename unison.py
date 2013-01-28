import os
import re
import subprocess
import sys

UNISON_BIN = 'unison'

PERMS_ALL = '-1'
PERMS_NONE = '0'
PERMS_DEFAULT = '0o1777'

class PathChangeStatus:
  OPERATION_NONE = 'none'
  OPERATION_UPDATE = 'update'
  OPERATION_CREATE = 'create'
  OPERATION_DELETE = 'delete'
  OPERATION_PROPERTIES = 'properties'
  OPERATION_SKIPPED = 'skipped'
  OPERATION_CONFLICT = 'conflict'

  TARGET_SRC = 'src'
  TARGET_DEST = 'dest'
  TARGET_NONE = 'none'

  _REGEXP_LINE = re.compile(r'^\[BGN\] (Copying|Deleting|Updating) ')
  _REGEXP_OPERATIONS = {
      OPERATION_CREATE: re.compile(r'^\[BGN\] Copying (?!properties)'),
      OPERATION_UPDATE: re.compile(r'^\[BGN\] Updating (file )?'),
      OPERATION_PROPERTIES: re.compile(r'^\[BGN\] Copying properties for '),
      OPERATION_DELETE: re.compile(r'^\[BGN\] Deleting ')}

  def __init__(self, path=None,
               operation=OPERATION_NONE,
               target=TARGET_NONE):
    self.path = path
    self.operation = operation
    self.target = target

  def __str__(self):
    return 'Path: %r\tOperation:%r\tTarget:%r' % (
        self.path, self.operation, self.target)

  @staticmethod
  def parse_unison_stderr(err, src, dest, debug=False):
    for line in iter(err.readline, b''):
      line = line.splitlines()[0]
      # print 'output line: %s' % line
      if debug:
        print line

      if PathChangeStatus._REGEXP_LINE.match(line):
        # Get a new item
        if debug:
          print line

        operation = PathChangeStatus.OPERATION_NONE
        prefix = '[BGN] '
        for op, r in PathChangeStatus._REGEXP_OPERATIONS.iteritems():
          m = r.match(line)
          if m:
            prefix = m.group(0)
            operation = op
            break

        field_to = ''
        field_from = ''
        if line.endswith(' to ' + src):
          target = PathChangeStatus.TARGET_SRC
          field_to = ' to ' + src
          field_from = ' from ' + dest
        elif line.endswith(' to ' + dest):
          target = PathChangeStatus.TARGET_DEST
          field_to = ' to ' + dest
          field_from = ' from ' + src
        elif line.endswith(' from ' + src):
          if operation == PathChangeStatus.OPERATION_DELETE:
            target = PathChangeStatus.TARGET_SRC
          else:
            target = PathChangeStatus.TARGET_DEST
          field_from = ' from ' + src
        elif line.endswith(' from ' + dest):
          if operation == PathChangeStatus.OPERATION_DELETE:
            target = PathChangeStatus.TARGET_DEST
          else:
            target = PathChangeStatus.TARGET_SRC
          field_from = ' from ' + dest
        else:
          target = PathChangeStatus.TARGET_NONE

        path = line[len(prefix):(
            len(line) - len(field_from) - len(field_to))]

        yield PathChangeStatus(path=path, operation=operation, target=target)


  @staticmethod
  def parse_unison_stdout(out):
    for line in iter(out.readline, b''):
      line = line.splitlines()[0]
      # print 'output line: %s' % line

      if len(line) > 13 and (line[9] == '<' or line[13] == '>'):
        # Get a new item
        # print line
        path = line[26:]
        path = path[:-2]
        operation = None
        if line[9] == '<' and line[13] != '>':
          target = PathChangeStatus.TARGET_SRC
          target_str = line[15:24].rstrip()
          dest_str = line[0:9].rstrip()
        elif line[9] != '<' and line[13] == '>':
          target = PathChangeStatus.TARGET_DEST
          target_str = line[0:9].rstrip()
          dest_str = line[15:24].rstrip()
        else:
          target = PathChangeStatus.TARGET_NONE
          operation = PathChangeStatus.OPERATION_CONFLICT

        if not operation and target != PathChangeStatus.TARGET_NONE:
          if target_str == 'changed' or target_str == 'props':
            operation = PathChangeStatus.OPERATION_UPDATE
          elif target_str == 'deleted':
            operation = PathChangeStatus.OPERATION_DELETE
          elif target_str[0:3] == 'new':
            operation = PathChangeStatus.OPERATION_CREATE
          else:
            if target != PathChangeStatus.TARGET_NONE:
              if dest_str:
                if target_str:
                  operation = PathChangeStatus.OPERATION_UPDATE
                else:
                  operation = PathChangeStatus.OPERATION_DELETE
              else:
                operation = PathChangeStatus.OPERATION_CREATE
            else:
              operation = PathChangeStatus.OPERATION_NONE

        yield PathChangeStatus(path=path, operation=operation, target=target)



def sync_with_unison(src_dir, dest_dir, force_dir=None, unison_path=None,
                     perms=PERMS_DEFAULT, times=False, debug=False):
  params = [UNISON_BIN, '-batch', '-confirmbigdel=false', '-perms', perms]
  params.append(src_dir)
  params.append(dest_dir)

  if times:
    params.append('-times')

  env = os.environ.copy()
  if unison_path:
    env['UNISON'] = unison_path

  if force_dir:
    params.append('-force')
    if force_dir == 1:
      params.append(src_dir)
    elif force_dir == 2:
      params.append(dest_dir)
    else:
      params.append(force_dir)

  change_list = []
  try:
    p = subprocess.Popen(
        params,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)
    change_list = []
    '''
    for item in PathChangeStatus.parse_unison_stdout(p.stdout):
      change_list.append(item)
      print 'Obtain: ' + str(item)
    '''
    for item in PathChangeStatus.parse_unison_stderr(
        p.stderr, os.path.abspath(src_dir), os.path.abspath(dest_dir),
        debug=debug):
      change_list.append(item)
      if debug:
        print 'Obtain: ' + str(item)
    return change_list

  except subprocess.CalledProcessError as e:
    return False

