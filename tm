#!/usr/bin/env bugger

##############################
# startup is always called
##############################
startup:
# TODO: assert we're in the right directory
  PWD=$ pwd
  BRANCH=$ hg qtop | sed 's/no patches applied/baseline/'
  BUILDDIR="@PWD/build_@BRANCH\_OPT.OBJ"
  BASELINEDIR="@PWD/build_baseline_OPT.OBJ"
  MAKE="make -j3"

##############################
# Task lists
##############################

Check:
  compile, trace-test, ref-test

Quick:
  compile, trace-test, sunspider, ubench

Full:
  compile, trace-test, ref-test, sunspider, v8, ubench, build-ff, dump-patch

Baseline: # run the benchmarks after popping all the directories
  PATCHNAME=$ hg qtop
  $ hg qpop -a
  compile (BASELINEDIR)
  sunspider (BASELINEDIR)
  v8 (BASELINEDIR)
  ubench (BASELINEDIR)
  $ hg qgoto @PATCHNAME

 

##############################
# Building
##############################
compile(DIR=BUILDDIR):
  possibly_configure
  $ @MAKE -C @DIR

possibly_configure(DIR=BUILDDIR):
  $ test -e @DIR || mkdir -p @DIR
  $ test -e @DIR/Makefile || (cd @DIR && ../configure)


build-ff:
  $ @MAKE -f client.mk build -C ../../


##############################
# Tests
##############################

trace-test(DIR=BUILDDIR):
  $ python trace-test/trace_test.py @DIR/js

ref-test(DIR=BUILDDIR):
  $ python tests/jstests.py @DIR/js --args="-j"


##############################
# Benchmarks
##############################
sunspider(DIR=BUILDDIR):
  $ ./sunspider --args="-j" --shell=@DIR/js --run=30 --suite=sunspider-0.9.1

v8(DIR=BUILDDIR):
  $ ./sunspider --args="-j" --shell=@DIR/js --run=30 --suite=v8-v4

ubench(DIR=BUILDDIR):
  $ ./sunspider --args="-j" --shell=@DIR/js --run=30 --suite=ubench


##############################
# Utils
##############################
# TODO: baseline is my own stuff
dump-patch:
  $ hg diff --rev baseline:. > `hg qtop`.patch
