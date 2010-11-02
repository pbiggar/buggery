#!/usr/bin/env bugger

##############################
# startup is always called
##############################
startup:
# TODO: assert we're in the right directory
  PWD=$ pwd
  BRANCH=$ hg qtop | sed 's/no patches applied/baseline/'
  OBJDIR_OPT="@PWD/build_@BRANCH\_OPT.OBJ"
  OBJDIR_DBG="@PWD/build_@BRANCH\_DBG.OBJ"
  OBJDIR_BASELINE="@PWD/build_baseline_OPT.OBJ"
  MAKE="make -j3"

##############################
# Task lists
##############################

Check:
  compile, test

Quick:
  compile, jit-test, sunspider, ubench

Full:
  compile, jit-test, ref-test, sunspider, v8, ubench, build-firefox, dump-patch

Baseline: # run the benchmarks after popping all the directories
  PATCHNAME=$ hg qtop
  $ hg qgoto baseline
  compile (OBJDIR_BASELINE)
  RETVAL=sunspider (OBJDIR_BASELINE)
  $ hg qgoto @PATCHNAME

# TODO:
#   if it starts with a capital letter, display it
#   if its a command with $$, display it
#   "display it" means show the command, then show the output. But also capture it.
#   add 'exists(..) or/and/not' type syntax for predicates
#   allow comments in many more places
#   multiple levels of indentation means continue the command or line
#     eg:
#       command:
#         $ asdasd
#           --some-flag
#           --another-flag
#   capture all flags, and apply them
#     check they can be applied before running any commands
#     all paths
#   allow all python functions to be called by prefixing them with 'py'
#     pyos.paths
#
#   rename RETVAL to RESULT, ala Eiffel
#
#   -v should go in, then out, maybe using indentation and '>' and '<'
#
#   do we check that parameters are passed or defined globally? we should
#

##############################
# Building
##############################
compile(DIR=OBJDIR_OPT, CONFIGURE_FLAGS="--enable-optimize --disable-debug"):
  possibly_configure (DIR, CONFIGURE_FLAGS)
  $ @MAKE -C @DIR

possibly_configure(DIR, CONFIGURE_FLAGS):
  $ test -e configure || autoconf213
  $ test -e @DIR || mkdir -p @DIR
  $ test -e @DIR/Makefile || (cd @DIR && ../configure @CONFIGURE_FLAGS --enable-threadsafe --with-system-nspr)


Build-firefox:
  $ @MAKE -f client.mk build -C ../../

Tags:
  $ ctags -R --languages=c,c++ .


##############################
# Tests
##############################
compile_debug:
  compile (OBJDIR_DBG, "--enable-debug --disable-optimize")

test:
  jit-test
  ref-test

jit-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  compile(DIR)
  $ python -u jit-test/jit_test.py @DIR/js @TEST-SPEC

ref-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  compile(DIR)
  $ python -u tests/jstests.py --args="-j -m" --no-progress @DIR/js @TEST-SPEC


##############################
# Benchmarks
##############################
Measure:
  FILE1=baseline
  FILE2=sunspider
  RETVAL=sunspider_compare(FILE1, FILE2, OBJDIR_BASELINE)

sunspider_compare(FILE1, FILE2, DIR):
  RETVAL=$ cd Sunspider && ./sunspider-compare-results @FILE1 @FILE2  --shell @DIR/js



sunspider(DIR=OBJDIR_OPT):
  compile(DIR)
  OUTPUT=$ cd SunSpider && ./sunspider --args="-j -m" --shell=@DIR/js --run=60 --suite=sunspider-0.9.1
  RETVAL=$ echo "@OUTPUT" | grep 'Results are located at' | sed 's/Results are located at //'

v8(DIR=OBJDIR_OPT):
  compile(DIR)
  $ cd SunSpider && ./sunspider --args="-j -m" --shell=@DIR/js --run=30 --suite=v8-v6

ubench(DIR=OBJDIR_OPT):
  compile(DIR)
  $ cd SunSpider && ./sunspider --args="-j -m" --shell=@DIR/js --run=30 --suite=ubench


##############################
# Utils
##############################
# TODO: baseline is my own stuff
dump-patch:
  $ hg diff --rev baseline:. > `hg qtop`.patch


newbug(BUGNUM):
  DIR="bug@BUGNUM"
  newclone (DIR)
  $ hg --cwd @DIR qimport bz://@BUGNUM

newclone(DIR):
  $ hg clone tracemonkey-clean @DIR
  $ echo "default-push = ssh://hg.mozilla.org/tracemonkey" >> @DIR/.hg/hgrc
  $ hg --cwd @DIR qinit -c 
  $ hg --cwd @DIR qimport -p ../sunspider.patch
  $ hg --cwd @DIR qimport -p ../single_apply.patch
  $ hg --cwd @DIR qnew baseline
