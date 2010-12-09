# Dynamically add tests for all files in the tests/errors/ directory. A test
# called 'a' would be added as "test_a", which means nose would pick it up.

def insert_file_tests():
  """Create a nosetest for each file in each sub-directory."""

  from nose.tools import raises
  import glob
  import pdb
  import os.path
  import re
  from buggery.exceptions import UserError
  from buggery import Parser

  def parse_test_comments(lines):
    result = {'output': '', 'args': '', 'task': 'test'}
    for line in lines:
      matches = re.match ('^\s*#\s*TEST-(\w+): (.*)$', lines)
      if matches != None:
        result[matches.groups()[1]] = matches.groups()[2]

    result['args'] = result['args'].split(' ')

    return result



  # If we directly create the inner functions, they'll all bind to the same
  # variable `contents`, which is not what we want.
  def gen_error_func(name, contents):
    @raises(UserError)
    def func():
      test_comments = parse_test_comments(contents)
      bugger = Parser().parse(contents)
      output = bugger.run(test_comments['task'], test_comments['args'])

    func.__name__ = name
    return func

  def gen_normal_func(name, contents):
    def func():
      bugger = Parser().parse(contents)

    func.__name__ = name
    return func

  def read_files(dir, func):
    for filename in glob.glob(__path__[0] + '/' + dir + "/*.bgr"):
      name = "test_" + dir + '_' + os.path.basename(filename)
      contents = file(filename).read()
      globals()[name] = func(name, contents)

  read_files("errors", gen_error_func)
  read_files("parsing", gen_normal_func)


insert_file_tests()

# Don't export symbols we don't intent to.
del insert_file_tests
