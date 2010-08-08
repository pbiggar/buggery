# Dynamically add tests for all files in the tests/errors/ directory. A test
# called 'a' would be added as "test_a", which means nose would pick it up.

def insert_error_tests():
  """Create a nosetest for each file in the error directory, and assert that it raises a UserError."""

  from nose.tools import raises
  import glob
  import pdb
  import os.path
  from buggery.exceptions import UserError
  from buggery import Parser

  for filename in glob.glob(__path__[0] + "/errors/*.bgr"):
    name = "test_" + os.path.basename(filename)
    contents = file(filename).read()

    # A function to generate the test functions we need. If we directly create
    # the functions, they'll all bind to the same variable `contents`, which
    # is not what we want.
    def gen_func(param):
      @raises(UserError)
      def func():
        Parser().parse(param)

      func.__name__ = name
      return func

    globals()[name] = gen_func(contents)

insert_error_tests()

# Don't export symbols we don't intent to.
del insert_error_tests
