#!/usr/bin/env python

import sys
from pprint import pprint
import ply.lex as lex
import ply.yacc as yacc
from lcdict import lcdict
from exceptions import UserError, CommandError
from nose.tools import raises
import subprocess
import shlex
import inspect
import re


class Parser(object):
  """Generate a nice AST to use later. We can implement the rule running as an AST walker.
  Here are the parser productions, ignoring syntactic tokens:

    # File
    file := task*

    # Task declarations
    task := ID parameter* subtask+
    parameter := ID default-value?
    default-value := string|variable
    variable := ID

    # Subtask declarations
    subtask := (ID? COMMAND)|(call*)
    call := ID argument*
    argument := string|variable

    # Final
    string := (string-literal|variable-interpolation)+
    variable-interpolation := ID

  The AST is slightly nicer:

    # File
    file := task*

    # Task declarations
    task := taskname:ID parameter* subtask+
    parameter := paramname:ID default-value?
    default-value := string|variable
    variable := varname:ID

    # Subtask declarations
    subtask := lvalue:ID? (COMMAND|call)
    call := taskname:ID argument*
    argument := string|variable
    lvalue := ID

    # Final
    string := (string-literal|variable-interpolation)+
    variable-interpolation := ID

  The AST is implemented as tuples containing the name of the production, followed by the parameters.
  Lists are wrapped in tuples as in: ('param-list' [('param', ...), ('param', ...)])

  """
  ID_syntax = r'[A-Za-z][a-zA-Z0-9_]*'
  var_syntax = r'[A-Z][A-Z0-9_]*'
  subtask_syntax = r'[a-z][a-z0-9_]*'
  task_syntax = r'[A-Za-z][a-z_]*'

  def parse(self, input):
    tokens = (
      'STRING',
      'ID',
      'INDENT',
      'COMMAND',
    )

    literals = ":,=()$"

    def t_STRING(t):
      r'"(\\.|[^\\"])*"'
      val = t.value[1:-1]
      val = re.sub(r'\\n', "\n", val);
      val = re.sub(r'\\t', "\t", val);
      t.value = StaticString(val)
      return t

    # Put this before TASKNAME
    def t_COMMAND(t):
      r'\$\s\S[^\n]*' # Starts with '$ ' then a character, and goes to the end of the line.
      t.value = Command(t.value[2:])
      return t

    # A task must flush left, be comprised entirely of lower-case letters and
    # hyphens (no CamelCase allowed), and may optionally start with an
    # upper-case letter to indicate top-level tasks. Underscores are not
    # allowed.
    # TODO: make tests for correct ID usage.

    def t_ID(t):
      r'[A-Za-z][a-zA-Z0-9_]*'
      return t

    def t_INDENT(t):
      r'(?<=\n)\ \ (?=\S)' # Exactly 2 spaces, preceeded by a \n, followed by non-whitespace
      t.lexer.lineno += 1
      return t

    # Low priority: Throw away the newlines that aren't indents
    def t_NEWLINE(t):
      r'\n'
      t.lexer.lineno += 1

    # Throw away remaining whitespace (low priority)
    def t_WHITESPACE(t):
      r'\s'

    # Throw away comments (low priority)
    def t_COMMENT(t):
      r'\#[^\n]*'
      pass


    def t_error(t):
      raise UserError("Lexing error (line %d): %s" % (t.lineno, str (t.__dict__)))

    def p_error(p):
      raise UserError("Parsing error (line %d): %s" % (p.lineno, str (p.__dict__)))


    def p_file(p):
      """
        file : task_list
      """
      p[0] = Buggery(p[1])


    def p_task_list(p):
      """
        task_list : task_list task
                  | empty
      """
      if len(p) == 2:
        p[0] = []
      else:
        p[0] = p[1] + [p[2]]


    def p_empty(p):
      """
        empty :
      """
      pass


    def p_task(p):
      """
        task : ID ':' subtask_lines
             | ID '(' param_list ')' ':' subtask_lines
      """
      name = p[1]
      if len(p) == 4:
        params = []
        subtasks = p[3]
      else:
        params = p[3]
        subtasks = p[6]

      p[0] = BuggeryTask (name, params, subtasks)
      if self.debug:
        print ("Completed a task:\n" + pprint.pformat(p[0]))


    def p_subtask_lines(p):
      """
        subtask_lines : subtask_lines subtask_line
                      | empty
      """
      if len(p) == 2:
        p[0] = []
      elif isinstance(p[2], list): # subtask_line can be a subtask_list
        p[0] = p[1] + p[2]
      else:
        p[0] = p[1] + [p[2]]


    # TODO: this is awkward - see if you can move the top 3 to the assignment production.
    def p_subtask_line(p):
      """
        subtask_line : INDENT lvalue call
                     | INDENT lvalue COMMAND
                     | INDENT lvalue STRING
                     | INDENT call_list
                     | INDENT COMMAND
      """
      if len(p) == 3:
        p[0] = p[2] # same for command or subtask_list

      else:
        p[0] = Assignment (p[2], p[3])


    def p_lvalue(p):
      """
        lvalue : ID '='
      """
      p[0] = p[1]


    def p_call_list(p):
      """
        call_list : call ',' call_list
                  | call
      """
      if len(p) == 2:
        p[0] = [p[1]]
      else:
        p[0] = [p[1]] + p[3]


    def p_call(p):
      """
        call : ID '(' arg_list ')'
             | ID
      """
      name = p[1]
      args = []
      if len(p) > 2:
        args = p[3]

      p[0] = Call(name, args)


    def p_arg_list(p):
      """
        arg_list : arg ',' arg_list
                 | arg
      """
      if len(p) == 2:
        p[0] = [p[1]]
      else:
        p[0] = [p[1]] + p[3]

    def p_arg(p):
      """
        arg : variable
            | STRING
      """
      p[0] = p[1]


    def p_param_list(p):
      """
        param_list : param ',' param_list
                   | param
      """
      if len(p) == 2:
        p[0] = [p[1]]
      else:
        p[0] = [p[1]] + p[3]


    def p_param(p):
      """
        param : ID
              | ID '=' default_param
      """
      name = p[1]
      default = None
      if len(p) == 4:
        default = p[3]

      p[0] = Param(name, default)


    def p_default_param(p):
      """
        default_param : arg
      """
      p[0] = p[1]




    def p_variable(p):
      """
        variable : ID
      """
      p[0] = Variable(p[1])




    def column_number(input, lexpos):
      last_cr = input.rfind('\n', 0, lexpos)
      if last_cr < 0:
        last_cr = 0
      column = (token.lexpos - last_cr) + 1
      return column


    debug = False
    self.debug = debug
    lex.lex(debug=debug)
    parser = yacc.yacc(debug=debug)
    buggery = parser.parse(input, debug=debug)
    buggery.check()
    return buggery


# Abstract classes
class Node(object):

  def traverse(self, callback_name, state):
    method = getattr(self, callback_name, None)
    if method != None:
      method(state)

    for k,v in self.__dict__.iteritems():
      self._nested_traverse(v, callback_name, state)

  def _nested_traverse(self, item, callback_name, state):
    """Check subelements for Nodes to be traversed"""
    if isinstance(item, Node):
      item.traverse(callback_name, state)

    elif isinstance(item, list):
      for elem in item: self._nested_traverse(elem, callback_name, state)

    elif isinstance(item, dict):
      for key,val in item.items():
        self._nested_traverse(val, callback_name, state)


  def __repr__(self):
    name = self.__class__.__name__.lower()
    attrs = str(self.__dict__)
    return '%s: %s' % (name, attrs)

class Subtask(Node):
  pass


# Concrete classes
class Task(Node):
  def __init__(self, name):
    self.name = name



class BuggeryTask(Task):

  def __init__(self, name, params, subtasks):
    super(BuggeryTask, self).__init__(name)
    self.params = params
    self.subtasks = subtasks


  def run(self, buggery, actuals):

    if buggery.options.verbose:
      print "Eval: %s(%s)" % (self.name, str([a.as_string() for a in actuals])[1:-1])

    # Copy the parameters into the stack frame
    for p in self.params:
      actual = actuals.pop(0)
      if actual == None:
        actual = p.default

      if actual == None:
        raise UserError("Null is not a valid value")

      buggery.set_var(p.name, actual)

    # Run subtasks
    for subtask in self.subtasks:
      subtask.eval(buggery)

    # There may not be a key. Ignore it so.
    try:
      return buggery.get_var("RETVAL")
    except:
      pass


  def _check(self, buggery):
    if len(self.subtasks) == 0:
      raise UserError ("Task %s has no subtasks" % self.name)



class PythonTask(Task):
  def __init__(self, name, function):
    super(PythonTask, self).__init__(name)
    self.function = function

  def run(self, buggery, actuals):
    vals = [actual.as_string() for actual in actuals]
    return self.function(*vals)


# eval always returns a Data object


class Assignment(Subtask):
  def __init__(self, lvalue, rvalue):
    self.lvalue = lvalue
    self.rvalue = rvalue

  def eval(self, buggery):
    result = self.rvalue.eval(buggery)
    buggery.set_var(self.lvalue, result)


class Command(Subtask):
  def __init__(self, command):
    self.command = command

  def eval(self, buggery):
    command = buggery.interpolate (self.command)

    if buggery.options.verbose:
      print "Eval: " + command

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    proc.wait()
    (stdout, stderr) = proc.communicate()

    result = ProcData(command=command,
                      stdin=None,
                      stdout=stdout,
                      stderr=stderr,
                      exit_code=proc.returncode,
                      pid=proc.pid)

    if proc.returncode != 0:
      raise CommandError(result)
    return result


class Call(Subtask):
  def __init__(self, target, args):
    self.target = target
    self.args = args

  def eval(self, buggery):
    actuals = [arg.eval(buggery) for arg in self.args]
    return buggery.run(self.target, actuals)


  def _check(self, buggery):
    if self.target not in buggery.tasks:
      raise UserError("Task %s not defined" % self.target)


class StaticString(Subtask):
  def __init__(self, string):
    self.string = string

  def eval(self, buggery):
    return StringData(buggery.interpolate(self.string))



class Variable(Node):
  def __init__(self, name):
    self.name = name

  def eval(self, buggery):
    return buggery.get_var(self.name)



class Param(Node):
  def __init__(self, name, default):
    self.name = name
    self.default = default


class Buggery(Node):
  def __init__(self, task_list):
    self.tasks = lcdict()
    self.add_tasks (task_list)
    self.stack = []
    self.globals = self.StackFrame()
    self.add_builtins()

    self.options = object()


  def add_tasks(self, task_list):
    for t in task_list:
      self.add_task(t)


  def add_task(self, task):
    if task.name in self.tasks:
      raise UserError("Duplicate task: %s" % task.name)

    self.tasks[task.name] = task

  def check(self):
    self.traverse("_check", self)

    if len(self.tasks) == 0:
      raise UserError("No tasks defined")

  class StackFrame(dict):
    pass


  def run(self, taskname, args, use_globals = False):
    if taskname not in self.tasks:
      raise UserError ("No task '%s' defined" % taskname)

    task = self.tasks[taskname]

    # New stackframe and copy parameters
    frame = self.StackFrame() if not use_globals else self.globals
    self.stack.insert(0, frame)

    # Run the task itself
    result = task.run(self, args)

    # Pop the stackframe
    self.stack.pop(0)

    return result


  def get_var(self, name):
    if name in self.globals:
      return self.globals[name]

    return self.stack[0][name]

  # There's no need for checking here, since all variable and global names are statically known, and can be statically checked.
  def set_var(self, name, value):
    self.stack[0][name] = value

  def interpolate(self, string):
    # TODO handle complex interpolation ("@{...}")

    # For string interpolation, using the @ symbol. A regex is sufficient for this.
    return re.sub(r'@' + Parser.var_syntax + '',
                  lambda m: self.get_var(m.group(0)[1:]).as_string(),
                  string)


  def help_string(self):
    result = "Available tasks:\n\n"

    for task in self.tasks:
      result += "\t %(task)s\n" % locals()

    return result

  def add_builtins(self):
    def my_print (string):
      print string

    self.add_task (PythonTask("print", my_print))






class Data(object):
  pass

class ProcData(Data):
  def __init__(self, command=None, stdin=None, stdout=None, exitcode=None, stderr=None, pid=None, exit_code=None):
    self.command = command
    self.stdin = stdin
    self.stdout = stdout
    self.stderr = stderr
    self.exit_code = exit_code
    self.pid = pid

  def eval(self, buggery):
    return self

  def as_string(self):
    return self.stdout


class StringData(Data):
  def __init__(self, string):
    assert (isinstance(string, str))
    self.string = string

  def eval(self, buggery):
    """Get actual value. This performs interpolation."""
    return buggery.interpolate(self.string)

  def as_string (self):
    return self.string



#raise Exception("No top-level task named: " + name)
# TODO: lots of test cases which don't raise, and which can be successfully parsed
def simple_buggery():
  return Parser().parse("mytask:\n  $ ls")

@raises(UserError)
def test_undefined_task():
  simple_buggery().run("undef_task", [])

def test_simple():
  simple_buggery().run("mytask", [])

# TODO: lost of case sensitive stuff. Everything must be lower case, except the first letter of top-level task definitions
# TODO: lots of bad naming. spaces, illegal chars,  etc.
