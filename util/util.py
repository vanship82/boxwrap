import os

def get_next(iterator):
  try:
    return iterator.next()
  except:
    return None

def path_for_sorting(path):
  return path.replace(os.pathsep, '\1')

