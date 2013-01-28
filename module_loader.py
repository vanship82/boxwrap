import inspect
import os
import sys

package_folder = os.path.realpath(os.path.dirname(os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))))

if package_folder not in sys.path:
  sys.path.insert(0, package_folder)


