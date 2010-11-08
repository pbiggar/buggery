#!/usr/bin/env python

import sys
import pprint
import ply.lex as lex
import ply.yacc as yacc
from lcdict import lcdict
from exceptions import UserError, CommandError
from nose.tools import raises
import subprocess
import shlex
import inspect
import re
import pdb

def bgrassert (cond):
  if not cond:
    print("Assertion failed: Condition is not true: " + str(cond))
    import pdb
    pdb.set_trace()



class Parser(object):
  """Generate a nice AST to use later. We can implement the rule running as an AST walker.

  The concrete grammar ignoring syntactic tokens:

    # File
    file := task*

    # Task declarations
    task := ID parameter* subtask+
    parameter := ID default-value?
    default-value := string|variable
    variable := ID

    # Subtask declarations
    subtask := subtask_list | assignment
    assignment := ID? (command | call)
    subtask_list := (command|call)+
    call := ID expr*
    command := expr string

    # Strings and interpolation
    string := (string-literal|variable-interpolation)+
    variable-interpolation := ID

  The abstract grammar is slightly nicer:

    # File
    file := task*

    # Task declarations
    task := taskname:ID parameter* subtask+
    parameter := paramname:ID default-value?
    default-value := string|variable # all expr here?
    variable := varname:ID

    # Subtask declarations
    subtask := lvalue:ID? expr
    expr := command | call | string
    call := taskname:ID expr*
    command := stdin:expr command:string

    # Final
    string := (string-literal|variable-interpolation)+
    variable-interpolation := expr


  """
  ID_syntax = r'[A-Za-z][a-zA-Z0-9-_]*'
  var_syntax = r'[A-Z][A-Z0-9-_]*'
  subtask_syntax = r'[a-z][a-z0-9-_]*'
  task_syntax = r'[A-Za-z][a-z-_]*'


  def parse(self, input):

    # Keep track of line numbers and such
    def column_number(lexpos):
      last_cr = input.rfind('\n', 0, lexpos)
      if last_cr < 0:
        last_cr = 0
      column = (lexpos - last_cr)
      return column

    def add_token_cursor(t):
      if not isinstance(t.value, str):
        t.value.lineno = 'todo'
        t.value.colno = 'todo'

    def add_parser_cursor(p):
      p[0].lineno = p.lineno(0)
      p[0].colno = column_number(p.lexpos(0))


    tokens = (
      'STRING',
      'ID',
      'INDENT',
      'COMMAND',
    )

    literals = ":,=()$"

    def t_STRING(t):
      r'"(\\.|[^\\"])*"'
      t.value = t.value[1:-1]
      t.value = transform_escapes(t.value)
      t.value = StringData(BStr(t.value))
      add_token_cursor(t)
      return t

    def transform_escapes (val):
      val = re.sub(r'\\r', "\r", val);
      val = re.sub(r'\\n', "\n", val);
      val = re.sub(r'\\t', "\t", val);
      return val

    # Put this before TASKNAME
    def t_COMMAND(t):
      t.value = t.value.strip()
      add_token_cursor(t)
      return t
    t_COMMAND.__doc__ = r'(?<=\$)\s*(\(' + Parser.var_syntax + r'\))?\s*\S[^\n]*' # Starts with '$', optional parenthesis, and goes to the end of the line.

    # A task must flush left, be comprised entirely of lower-case letters and
    # hyphens (no CamelCase allowed), and may optionally start with an
    # upper-case letter to indicate top-level tasks. Underscores are not
    # allowed.


    # TODO: make tests for correct ID usage.
    def t_ID(t):
      add_token_cursor(t)
      return t
    t_ID.__doc__ = Parser.ID_syntax

    def t_INDENT(t):
      r'(?<=\n)\ \ (?=\S)' # Exactly 2 spaces, preceeded by a \n, followed by non-whitespace
      add_token_cursor(t)
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
      raise UserError("Lexing error (line %d): %s" % (t.lineno, str (t.__dict__)), None)

    def p_error(p):
      raise UserError("Parsing error (line %d): %s" % (p.lineno, str (p.__dict__)), None)


    def p_file(p):
      """
        file : task_list
      """
      p[0] = Buggery(p[1])
      add_parser_cursor(p)


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
      add_parser_cursor(p)
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


    def p_subtask_line(p):
      # RHS can be any expression if lvalue provided.
      # One of more calls (call-list)
      """
        subtask_line : INDENT lvalue expr
                     | INDENT call_list
                     | INDENT command
      """
      if len(p) == 3:
        p[0] = p[2] # same for command or call_list

      else:
        p[0] = Assignment (p[2], p[3])
        add_parser_cursor(p)

    def p_expr(p):
      """
        expr : command
             | call
             | STRING
      """
      p[0] = p[1]
      add_parser_cursor(p)


    def p_command(p):
      """
      command : '$' COMMAND
      """
      # COMMAND may start with a variable in parens, which is hard to split out with the lexer. So do it here.
      command = p[2]
      stdin = None
      if command[0] == '(':
        m = re.match(r'\(\s*(' + Parser.var_syntax + ')\s*\)?(.*)', command)

        stdin = m.group(1).strip()
        command = m.group(2).strip()

      p[0] = Command(BStr(command), stdin)
      add_parser_cursor(p)


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
      add_parser_cursor(p)


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
      add_parser_cursor(p)


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
      add_parser_cursor(p)





    debug = False
    self.debug = debug
    lex.lex(debug=debug)
    parser = yacc.yacc(debug=debug)
    buggery = parser.parse(input, debug=debug, tracking=True)
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

  def param_count(self):
    return len(self.params)

  def required_param_count(self):
    return len([p for p in self.params if not p.default])

  def run(self, buggery, actuals, caller):

    if buggery.options.verbose:
      str_actuals = [a.as_string() for a in actuals]
      str_actuals = [a if len(a) < 80 else a[0:77] + '...' for a in str_actuals]
      print "Eval: %s %s" % (self.name, " ".join(str_actuals))

    # Copy the parameters into the stack frame
    for p in self.params:
      try:
        actual = actuals.pop(0).eval(buggery)
      except IndexError:
        if p.default:
          actual = p.default.eval(buggery)
        else:
          raise UserError("Less parameters than expected", caller or self)

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

  # The startup task has defs which become global variables, so we need to define this
  def defs(self):
    l = []
    x = [st.defs() for st in self.subtasks]
    map(l.extend, x)
    return l

  def returns_value (self):
    return "RETVAL" in self.defs()



  def _check(self, buggery):
    if len(self.subtasks) == 0:
      raise UserError ("Task %s has no subtasks" % self.name, self)

    self.check_initialized_variables(buggery)
    self.check_return_values(buggery)

  def check_return_values(self, buggery):
    for st in self.subtasks:
      if isinstance(st, Assignment):
        if isinstance (st.rvalue, Call):
          name = st.rvalue.target
          if not buggery.get_task (name).returns_value():
            raise UserError ("Task %s does not return a value" % name, st.rvalue)




  def check_initialized_variables(self, buggery):

    # We can statically check all uninitialized variables, since the control flow is linear.
    inited_vars = set()

    # Add the parameters
    inited_vars = inited_vars.union([p.name for p in self.params])

    # Add the globals
    if self.name != 'startup':
      inited_vars = inited_vars.union(buggery.get_global_variable_names())

    # Check
    for st in self.subtasks:
      for var in st.uses():
        if var not in inited_vars:
          raise UserError ("Variable %s is used uninitialized" % var, st)

      # Add defined variables
      inited_vars = inited_vars.union(st.defs())



class PythonTask(Task):
  def __init__(self, name, function):
    super(PythonTask, self).__init__(name)
    self.function = function

  def run(self, buggery, actuals, caller):
    vals = [actual.as_string() for actual in actuals]
    return self.function(*vals)

  def param_count(self):
    (args, varargs, varkw, defaults) = inspect.getargspec(self.function)
    return len(args)

  def required_param_count(self):
    (args, varargs, varkw, defaults) = inspect.getargspec(self.function)
    count = len(args)
    if defaults: # this can be None
      count -= len(defaults)

    return count

  def defs(self):
    return []


class Assignment(Subtask):
  def __init__(self, lvalue, rvalue):
    assert (not isinstance (rvalue, str))
    self.lvalue = lvalue
    self.rvalue = rvalue

  def eval(self, buggery):
    result = self.rvalue.eval(buggery)
    buggery.set_var(self.lvalue, result)

  def uses(self):
    return self.rvalue.uses()

  def defs(self):
    return [self.lvalue]


class Command(Subtask):
  def __init__(self, command, stdin_var):
    self.command = command
    self.stdin_var = stdin_var

  def eval(self, buggery):
    command = self.command.interpolate(buggery, self)

    if buggery.options.verbose:
      print "    $ " + command

    stdin_str, stdin_proc = None, None
    if self.stdin_var:
      stdin_str = buggery.get_var(self.stdin_var).as_string()
      stdin_proc = subprocess.PIPE


    outs = ["", ""]

    def add_output(_out, _err):
      outs[0] += _out
      outs[1] += _err

      sys.stdout.flush()
      sys.stderr.flush()

      if buggery.options.verbose:
        sys.stdout.write(_out)
        sys.stdout.flush()
        sys.stderr.write(_err)
        sys.stderr.flush()


    try:
      proc = subprocess.Popen(command, stdin=stdin_proc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, bufsize=0)

      if stdin_str:
        proc.stdin.write(stdin_str)

      # Read directly so that we can save it and output it
      # TODO: make this work with stderr too, possibly by using pexpect (where available)
      while proc.poll() is None:
        out = proc.stdout.read(1)
        err = ''
        add_output(out, err)

      # Flush the remaining data
      add_output(proc.stdout.read(), proc.stderr.read())

    except KeyboardInterrupt, e:
      add_output(proc.stdout.read(), proc.stderr.read())

    stdout, stderr = outs[0], outs[1]
    result = ProcData(command=command,
                      stdin=stdin_str,
                      stdout=stdout.strip(),
                      stderr=stderr.strip(),
                      exit_code=proc.returncode,
                      pid=proc.pid)

    if proc.returncode != 0:
      raise CommandError(result)
    return result

  def uses(self):
    return self.command.uses()

  def defs(self):
    return set()


class Call(Subtask):
  def __init__(self, target, args):
    self.target = target
    self.args = args

  def eval(self, buggery):
    actuals = [arg.eval(buggery) for arg in self.args]
    return buggery.run(self.target, actuals, self)


  def _check(self, buggery):
    if self.target not in buggery.tasks:
      raise UserError("Task '%s' not defined" % self.target, self.target)

    arg_count = len(self.args)
    param_count = buggery.tasks[self.target].param_count()
    if arg_count > param_count:
      raise UserError("Task '%s' called with %s arguments, though there are only %s parameters" % (self.target, arg_count, param_count), self)

    required_param_count = buggery.tasks[self.target].required_param_count()
    if arg_count < required_param_count:
      raise UserError("Task '%s' called with %s arguments, but %s parameters are required" % (self.target, arg_count, required_param_count), self)

  def uses(self):
    return set([var.name for var in self.args if isinstance(var, Variable)])

  def defs(self):
    return set()


class Variable(Node):
  def __init__(self, name):
    self.name = name

  def eval(self, buggery):
    return buggery.get_var(self.name, self)



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

    class RespondFalse(object):
      def __getattr__(*args, **kwargs):
        return False

    self.options = RespondFalse()


  def add_tasks(self, task_list):
    for t in task_list:
      self.add_task(t)


  def add_task(self, task):
    if task.name in self.tasks:
      raise UserError("Duplicate task: %s" % task.name, task)

    self.tasks[task.name] = task

  def get_task(self, name):
    return self.tasks[name]

  def check(self):
    self.traverse("_check", self)

    if len(self.tasks) == self.num_builtins:
      raise UserError("No tasks defined", None)

  class StackFrame(dict):
    pass


  def run(self, taskname, args, caller=None):

    if taskname not in self.tasks:
      raise UserError ("No task '%s' defined" % taskname, None)

    task = self.tasks[taskname]

    # New stackframe and copy parameters
    use_globals = (taskname == "startup")
    frame = self.StackFrame() if not use_globals else self.globals
    self.stack.insert(0, frame)

    # Run the task itself
    result = task.run(self, args, caller)

    # Pop the stackframe
    self.stack.pop(0)

    return result


  def get_var(self, name, stateobj=None):
    if name in self.globals:
      return self.globals[name]

    if name in self.stack[0]:
      return self.stack[0][name]

    raise UserError ("Unknown variable: %s" % name, stateobj)

  # There's no need for checking here, since all variable and global names are statically known, and can be statically checked.
  def set_var(self, name, value):
    bgrassert (isinstance (value, Data))
    self.stack[0][name] = value

  def get_global_variable_names(self):
    if 'startup' in self.tasks:
      return self.tasks['startup'].defs()

    return []


  def help_string(self):
    result = "Available tasks:\n\n"

    for task in self.tasks:
      result += "\t %(task)s\n" % locals()

    return result

  def add_builtins(self):
    def builtin_print (string):
      print string

    def builtin_pass ():
      pass

    def builtin_save(filename, string):
      import os.path
      file(os.path.expanduser(filename), 'w').write(string)

    def builtin_append(filename, string):
      import os.path
      file(os.path.expanduser(filename), 'a').write(string)

    self.add_task (PythonTask("print", builtin_print))
    self.add_task (PythonTask("save", builtin_save))
    self.add_task (PythonTask("append", builtin_append))
    self.add_task (PythonTask("pass", builtin_pass))
    self.num_builtins = 4

  def has_task(self, name):
    return name in self.tasks



class BStr(str):
  """Buggery string, the base for all strings, is interpolable"""

  def interpolate(self, buggery, stateobj=None):
    # TODO handle complex interpolation ("@{...}")

    # For string interpolation, using the @ symbol. A regex is sufficient for this.
    return re.sub(r'@' + Parser.var_syntax + '',
                  lambda m: buggery.get_var(m.group(0)[1:], stateobj).as_string(),
                  self)

  def uses(self):
    return re.findall (r'@(' + Parser.var_syntax + ')', self)





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
    assert (isinstance(string, BStr))
    self.string = string

  def eval(self, buggery):
    return StringData(BStr(self.string.interpolate(buggery)))

  def uses(self):
    return self.string.uses()

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
