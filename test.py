import os
import sys
import unittest

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print "Usage: %s path/to/test" % sys.argv[0]
    sys.exit(0)
  import module_loader
  if len(os.path.dirname(sys.argv[1])):
    sys.path.insert(0, os.path.dirname(sys.argv[1]))
  m = __import__(os.path.basename(sys.argv[1]))
  del sys.argv[1]
  try:
    attrlist = m.__all__
  except AttributeError:
    attrlist = dir(m)
  for attr in attrlist:
    globals()[attr] = getattr(m, attr)

  unittest.main()
