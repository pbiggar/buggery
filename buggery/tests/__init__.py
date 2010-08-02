# Dynamically add tests for all files in the tests/errors/ directory. A test
# called 'a' would be added as "test_a", which means nose would pick it up.

def insert_error_tests():
  """Create a nosetest for each file in the error directory, and assert that it raises a UserError."""

  from nose.tools import raises
  import glob
  import pdb
  import os.path

  for filename in glob.glob(__path__[0] + "/errors/*"):
    name = "test_" + os.path.basename(filename)
    contents = file(filename).read()

    @raises(Exception)
    def func():
      Parser.parse(contents)

    func.__name__ = name
    globals()[name] = func

insert_error_tests()

# Don't export symbols we don't intent to.
del insert_error_tests
