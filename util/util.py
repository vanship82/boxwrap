import os


def get_next(iterator):
  try:
    return iterator.next()
  except:
    return None


def path_for_sorting(path):
  return path.replace(os.sep, '\1')


def merge_two_iterators(iter1, iter2, key_func):
  item1 = get_next(iter1)
  item2 = get_next(iter2)
  while True:
    key1 = key_func(item1) if item1 else None
    key2 = key_func(item2) if item2 else None
    if key1 == key2:
      if key1 is None:
        break
      yield item1, item2
      item1 = get_next(iter1)
      item2 = get_next(iter2)
    elif key1 is not None and (key1 < key2 or key2 is None):
      yield item1, None
      item1 = get_next(iter1)
    elif key2 is not None and (key1 > key2 or key1 is None):
      yield None, item2
      item2 = get_next(iter2)


