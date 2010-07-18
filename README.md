==============================
Buggery tutorial 
==============================

This is not intended to be a tutorial, or to state the purpose or describe the
use of the language. This just documents all the strutures and edge cases.


File structure
---------------

A buggery file is called 'buggery', or ends in '.buggery'.

The file consists entirely of lists of tasks.


Tasks
----------------

Minimally, tasks consist of a name, and a list of subtasks. All tasks are
written with their name flush against left side of the file, with no
indentation.

The simplest task is the empty task. It consists merely of its name follwed by
a colon:

    Mytask:


Tasks typically contain lists of subtasks.

There are two kinds of subtasks:

  * Nested subtasks are simply names of other subtasks
  * Command subtasks consist of a shell command, and begin with a $.

Here is a very simple buggery file containing 4 tasks, each with subtasks.


    Quick:
      compile
      test
      benchmark

    Compile:
      



    



A bugg


A buggery file is comprised of a long list of tasks.  A task is written::

  Task:
    list
    of
    subtasks

That is, to define a task, write its name with no indentation before it, then a ':'.  Top-level tasks start with a capital letter, may be called from the command line by running 'bugger TASKNAME', where TASKNAME is the name of the task you want to run. At program startup, the rule 'startup' is always called.

Each task is made up of a list of subtasks.  There are a few kinds of subtask:
  - a command subtask
  - a nested subtask

A nested subtask is simple, it just calls another task. It can have a parameter, and you may specify a list of them on the same line, separating them by commas.

A command subtask calls the shell with the given string.

Variables are also allowed. Save a result into a variable using any of::

  VARNAME=$ command # Returns the string output of calling `command`
  VARNAME="some string"

You can use variables in any other place using string-interpolation::

  $ make -f $MAKEFILE

Tasks have parameters, which should always have a default value! The default value will be used it is called without arguments.

Comments start with #, and have the bug that they cannot be escaped in the buggery file.

Any shell command which fails throws an exception, and does not continue. However, it may often be necessary to clean up your state. The can be done by adding multiple levels of nesting. TODO. Any level above that level will still be executed. This should only be used to clean up.

In general, any rule should end up with the same rough state. I may ammend that to say that rules may start with ! in order to signal that they are destructive.



