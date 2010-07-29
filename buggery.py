#!/usr/bin/env python

import string
import pprint
import sys
import os
import glob
import re
import ply.lex as lex
import ply.yacc as yacc


class Error(Exception):
  pass

class WhatToDo(Exception):
  pass


class Parser(object):
  """Generate a nice AST to use later. We can implement the rule running as an AST walker.
  Here are the parser productions, ignoring syntactic tokens:

    # File
    file := task*

    # Task declarations
    task := ID parameter* subtask_line+
    parameter := ID default-value?
    default-value := string|variable
    variable := ID

    # Subtask declarations
    subtask_line := ID? COMMAND|(subtask*)
    subtask := ID argument*
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
    subtask := lvalue:ID? (COMMAND|taskname:ID argument*) # don't like this - move into subtask - but call it something else.
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
      t.value = ('STRING', t.value)
      return t

    # Put this before TASKNAME
    def t_COMMAND(t):
      r'\$\s\S[^\n]*' # Starts with '$ ' then a character, and goes to the end of the line.
      t.value = t.value[2:]
      t.value = ('COMMAND', t.value)
      return t

    # A task must flush left, be comprised entirely of lower-case letters and
    # hyphens (no CamelCase allowed), and may optionally start with an
    # upper-case letter to indicate top-level tasks. Underscores are not
    # allowed.
    def t_ID(t):
      r'[A-Za-z][a-zA-Z0-9\-]*'
      t.value = ('ID', t.value)
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
      raise Error()


    def p_file(p):
      """
        file : task_list
      """
      p[0] = ('file', p[1])


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
      p[0] = ('task', name, ('param-list', params), ('subtask-list', subtasks))
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
        subtask_line : INDENT assignment subtask
                     | INDENT assignment COMMAND
                     | INDENT assignment STRING
                     | INDENT subtask_list
                     | INDENT COMMAND
      """
      if len(p) == 3:
        p[0] = p[2] # same for command or subtask_list

      else:
        p[0] = ('assignment', p[2], p[3])


    def p_assignment(p):
      """
        assignment : ID '='
      """
      if len(p) != 2:
        p[0] = p[1]


    def p_subtask_list(p):
      """
        subtask_list : subtask ',' subtask_list
                     | subtask
      """
      if len(p) == 2:
        p[0] = [p[1]]
      else:
        p[0] = [p[1]] + p[3]

    def p_subtask(p):
      """
        subtask : ID '(' arg_list ')'
                | ID
      """
      if len(p) == 2:
        p[0] = ('subtask', p[1], ('arg-list', []))
      else:
        p[0] = ('subtask', p[1], ('arg-list', p[3]))


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
      p[0] = p[1]

    def p_default_param(p):
      """
        default_param : arg
      """
      p[0] = p[1]




    def p_variable(p):
      """
        variable : '$' ID
      """
      p[0] = ('variable', p[2])




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
    lex.lex(debug=debug)
    parser = yacc.yacc(debug=debug)
    return parser.parse(input, debug=debug)



#raise Exception("Task already exists: " + name)
#raise Exception("Subtask has no task:" + subtask)
#raise Exception("Undefined task: " + name)
#raise Exception("No top-level task named: " + name)


