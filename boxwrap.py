import compression
import os
import shutil
import sys
import unison

class BoxWrap:

  def __init__(self, working_dir, cloud_dir, intermediate_base,
               reinit=False,
               unison_path=None, password=None,
               encryption_method=compression.ENCRYPTION_AES_256):
    self.working_dir = working_dir
    self.cloud_dir = cloud_dir
    self.intermediate_base = intermediate_base
    self.unison_path = unison_path
    self.password = password
    self.encryption_method = encryption_method

    self.working_original_im = self.check_and_init_intermediate_dir(
        os.path.join(intermediate_base, 'working_orignal'),
        force=reinit)
    self.cloud_original_im = self.check_and_init_intermediate_dir(
        os.path.join(intermediate_base, 'cloud_orignal'),
        sync_dir=self.working_original_im,
        force=reinit)
    self.cloud_wrapped_im = self.check_and_init_intermediate_dir(
        os.path.join(intermediate_base, 'cloud_wrapped'),
        force=reinit)
    self.working_wrapped_im = self.check_and_init_intermediate_dir(
        os.path.join(intermediate_base, 'working_wrapped'),
        sync_dir=self.cloud_wrapped_im,
        force=reinit)

  def check_and_init_intermediate_dir(self, directory, sync_dir=None,
                                      force=False):
    if force or os.path.isfile(directory):
      os.path.remove(directory)
    if not os.path.exists(directory):
      os.makedirs(directory)
      if sync_dir:
        unison.sync_with_unison(sync_dir, directory, force_dir=sync_dir,
                                times=True, unison_path=self.unison_path)
    return directory

  def apply_src_change_list(self, change_list, src, dest, is_compression):
    for item in change_list:
      print 'Process ' + str(item)
      if item.target != unison.PathChangeStatus.TARGET_DEST:
        continue

      if (item.operation == unison.PathChangeStatus.OPERATION_UPDATE or
          item.operation == unison.PathChangeStatus.OPERATION_CREATE):
        src_path = os.path.join(src, item.path)
        dest_path = os.path.join(dest, item.path)
        if os.path.exists(dest_path):
          if os.path.isfile(dest_path):
            os.remove(dest_path)
          else:
            shutil.rmtree(dest_path)

        if is_compression:
          print 'Compress From ' + src_path + ' to ' + compression.get_compressed_filename(dest_path)
          compression.compress_recursively(
              item.path, src, dest,
              password=self.password,
              encryption_method=self.encryption_method)
        else:
          print 'Decompress From ' + src_path + ' to ' + compression.get_original_filename(dest_path)
          compression.decompress_recursively(
              item.path, src, dest,
              password=self.password)

      elif item.operation == unison.PathChangeStatus.OPERATION_DELETE:
        dest_path = os.path.join(dest, item.path)
        if os.path.isdir(dest_path):
          shutil.rmtree(dest_path)
        else:
          os.remove(dest_path)

  def _sync_prefer_src(self, src, dest):
    print '*'*20 + 'step 1'
    change_list = unison.sync_with_unison(
        src, dest,
        force_dir=None,
        perms=unison.PERMS_NONE, times=False,
        unison_path=self.unison_path)
    print '*'*20 + 'step 2'
    change_list.extend(unison.sync_with_unison(
        src, dest,
        force_dir=None,
        perms=unison.PERMS_DEFAULT, times=True,
        unison_path=self.unison_path))
    print '*'*20 + 'step 3'
    change_list.extend(unison.sync_with_unison(
        src, dest,
        force_dir=src,
        perms=unison.PERMS_DEFAULT, times=True,
        unison_path=self.unison_path))
    return change_list

  def _has_dest_change(self, change_list):
    for item in change_list:
      if item.target == unison.PathChangeStatus.TARGET_DEST:
        return True
    return False

  def _handle_uncompressed_files(self, error_list, path):
    for item in error_list:
      print 'Compress ' + item + ' in ' + path
      item_path = os.path.join(path, item)
      if os.path.exists(item_path):
        compression.compress_file(
            item_path,
            compression.get_compressed_filename(item_path),
            password=self.password,
            encryption_method=self.encryption_method)
        os.remove(item_path)

  def sync(self):
    error_list = compression.test_decompress_recursively(
        '', self.cloud_dir, password=self.password)
    fatal_error = False
    for item in error_list:
      if compression.is_compressed_filename(item):
        fatal_error = True
        break
    if fatal_error:
      return

    self._handle_uncompressed_files(error_list, self.cloud_dir)

    print '*'*10 + 'Initial sync working'
    working_change_list = unison.sync_with_unison(
        self.working_dir, self.working_original_im,
        force_dir=self.working_dir,
        perms=unison.PERMS_DEFAULT, times=True,
        unison_path=self.unison_path)

    print '*'*10 + 'Initial sync cloud'
    cloud_change_list = unison.sync_with_unison(
        self.cloud_dir, self.cloud_wrapped_im,
        force_dir=self.cloud_dir,
        perms=unison.PERMS_DEFAULT, times=True,
        unison_path=self.unison_path)

    rnd = 1
    while (self._has_dest_change(working_change_list) or
        self._has_dest_change(cloud_change_list)):
      print '*'*10 + 'Round ' + str(rnd)
      rnd = rnd + 1
      print '*'*10 + 'Apply to working'
      self.apply_src_change_list(working_change_list, self.working_dir,
                                 self.working_wrapped_im, True)
      print '*'*10 + 'Apply to cloud'
      self.apply_src_change_list(cloud_change_list, self.cloud_dir,
                                 self.cloud_original_im, False)

      print '*'*10 + 'Sync between working original and cloud original'
      self._sync_prefer_src(self.working_original_im, self.cloud_original_im)
      print '*'*10 + 'Sync between cloud wrapped and working wrapped'
      self._sync_prefer_src(self.cloud_wrapped_im, self.working_wrapped_im)

      # Redo the syncing again to see any difference
      print '*'*10 + 'Next sync working'
      working_change_list = self._sync_prefer_src(
          self.working_dir, self.working_original_im)
      print '*'*10 + 'Next sync cloud'
      cloud_change_list = self._sync_prefer_src(
          self.cloud_dir, self.cloud_wrapped_im)


if __name__ == "__main__":
  if len(sys.argv) < 4:
    print 'usage: %s working cloud intermediate unison [password] [reinit]' % sys.argv[0]
    sys.exit(0)

  boxwrap = BoxWrap(sys.argv[1], sys.argv[2], sys.argv[3],
                    reinit=len(sys.argv) > 6,
                    unison_path=sys.argv[4],
                    password=sys.argv[5] if len(sys.argv) > 5 else None)
  boxwrap.sync()

