#!./bugger

# This file is a DSL- TODO convert to yaml
# Each task contains a list of subtasks.
# Sub-tasks starting with $ are shell commands.
# Tasks with a capital letter are exposed to the user.

##############################
# Startup is always called
##############################
Startup:
  PWD=$ pwd
  BRANCH=$ hg qtop
  BUILDDIR="$PWD/build_$BRANCH\_OPT.OBJ"
  BASELINEDIR="$PWD/build_baseline_OPT.OBJ"
  MAKE="make -j3"

##############################
# Task lists
##############################
Default:
  full

Quick:
  compile, trace-test, sunspider, ubench

Full:
  compile, trace-test, ref-test, sunspider, v8, ubench, build-ff, dump-patch

Baseline: # run the benchmarks after popping all the directories
  PATCHNAME=$ hg qtop
  $ hg qpop -a
  compile($BASELINEDIR)
  sunspider($BASELINEDIR)
  v8($BASELINEDIR)
  ubench($BASELINEDIR)
  $ hg qgoto $PATCHNAME

 

##############################
# Building
##############################
compile(DIR = $BUILDDIR):
  $ cd $DIR && $MAKE

build-ff:
  $ cd ../../ && $MAKE -f client.mk build


##############################
# Tests
##############################

trace-test(DIR = $BUILDDIR):
  $ python trace-test/trace-test.py $DIR/js

ref-test(DIR = $BUILDDIR):
  $ cd $DIR && python ../tests/jstests.py ./js --args="-j"


##############################
# Benchmarks
##############################
sunspider(DIR = $BUILDDIR):
  $ ./sunspider --args="-j" --shell=$DIR/js --run=30 --suite=sunspider-0.9.1

v8(DIR = $BUILDDIR):
  $ ./sunspider --args="-j" --shell=$DIR/js --run=30 --suite=v8-v4

ubench(DIR = $BUILDDIR):
  $ ./sunspider --args="-j" --shell=$DIR/js --run=30 --suite=ubench


##############################
# Utils
##############################
# TODO: qfulldiff is only in my .hgrc file
# TODO: 
dump-patch:
  $ hg qfulldiff > `hg qtop`.patch
