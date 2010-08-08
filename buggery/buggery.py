#!/usr/bin/env python

import sys
from pprint import pprint
import ply.lex as lex
import ply.yacc as yacc
from lcdict import lcdict


class UserError(Exception):
  pass

class WhatToDo(Exception):
  pass


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


  def parse(self, input):
    tokens = (
      'STRING',
      'ID',
      'INDENT',
      'COMMAND',
    )

    literals = ":,=()$"

    # TODO: this doesn't allow escaping of strings, nor single-quoted strings.
    def t_STRING(t):
      r'"[^"]*"'
      return t

    # Put this before TASKNAME
    def t_COMMAND(t):
      r'\$\s\S[^\n]*' # Starts with '$ ' then a character, and goes to the end of the line.
      t.value = t.value[2:]
      return t

    # A task must flush left, be comprised entirely of lower-case letters and
    # hyphens (no CamelCase allowed), and may optionally start with an
    # upper-case letter to indicate top-level tasks. Underscores are not
    # allowed.
    def t_ID(t):
      r'[A-Za-z][a-zA-Z0-9\-]*'
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




    def p_error(p):
      print p.__dict__
      raise UserError()


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

      p[0] = Task (name, params, subtasks)
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
      params = []
      if len(p) == 4:
        params = p[3]

      p[0] = Call(name, params)


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
        variable : '$' ID
      """
      p[0] = Variable(p[2])




    def t_error(p):
      print p
      sys.exit(1)

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
  def __init__(self, name, params, subtasks):
    self.name = name
    self.params = params
    self.subtasks = subtasks


  def _check(self, buggery):
    if len(self.subtasks) == 0:
      raise UserError ("Task %s has no subtasks" % self.name)


class Assignment(Node):
  def __init__(self, lvalue, rvalue):
    self.lvalue = lvalue
    self.rvalue = rvalue


class Command(Subtask):
  def __init__(self, command):
    self.command = command


class Call(Subtask):
  def __init__(self, target, args):
    self.target = target
    self.args = args

  def _check(self, buggery):
    if self.target not in buggery.tasks:
      raise UserError("Task %s not defined" % self.target)

class Variable(Node):
  def __init__(self, name):
    self.name = name

class Param(Node):
  def __init__(self, name, default):
    self.name = name
    self.default = default


class Buggery(Node):
  def __init__(self, task_list):
    self.tasks = lcdict()
    self.add_tasks (task_list)

  def add_tasks(self, task_list):
    for t in task_list:
      self.add_task(t)

  def add_task(self, task):
    if task.name in self.tasks:
      raise UserError("Duplicate task: %s" % task.name)

    self.tasks[task.name] = task


  def check(self):
    self.traverse("_check", self)


#raise Exception("Task already exists: " + name)
#raise Exception("Subtask has no task:" + subtask)
#raise Exception("Undefined task: " + name)
#raise Exception("No top-level task named: " + name)

def right_number_of_params():
  raise Exception

def simple_task():
  raise Exception

# TODO: lost of case sensitive stuff. Everything must be lower case, except the first letter of top-level task definitions
