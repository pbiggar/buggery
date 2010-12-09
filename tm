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
  OBJDIR_NJN="@PWD/build_@BRANCH\_NJN.OBJ"
  OBJDIR_BASELINE_OPT="@PWD/build_baseline_OPT.OBJ"
  OBJDIR_BASELINE_DBG="@PWD/build_baseline_DBG.OBJ"
  OBJDIR_BASELINE_NJN="@PWD/build_baseline_NJN.OBJ"
  MAKE="make -j3"

# OSX: Gary Kwong from 612809 comment 1
  CROSS32_O1 = "CC='gcc-4.2 -arch i386' CXX='g++-4.2 -arch i386' HOST_CC='gcc-4.2' HOST_CXX='g++-4.2' RANLIB=ranlib AR=ar AS=$CC LD=ld STRIP='strip -x -S' CROSS_COMPILE=1 ../configure --target=i386-apple-darwin8.0.0 --enable-debug --disable-optimize --disable-tests"

# OSX: Boris Zbarsky from 612809 comment 17
  CROSS32_O2="env CC='gcc-4.2 -arch i386' CXX='g++-4.2 -arch i386' AR=ar CROSS_COMPILE=1 ../configure --enable-optimize --disable-debug --target=i386-apple-darwin9.2.0 --enable-macos-target=10.5"

# OSX: Nicholas Nethercote by email
  CROSS32_O3="CC='gcc -m32' CXX='g++ -m32' AR=ar ../configure --enable-debug --disable-optimize --target=i386-darwin"

# OSX: From MOZCONFIG via browser build
  CROSS32_O4="../configure  --enable-application=browser --target=i386-apple-darwin9.2.0 --with-macos-sdk=/Developer/SDKs/MacOSX10.5.sdk --enable-macos-target=10.5 --enable-threadsafe --enable-ctypes --disable-shared-js"

# OSX: Minimum that should work
  CROSS32_O5="../configure --target=i386-apple-darwin9.2.0 --with-macos-sdk=/Developer/SDKs/MacOSX10.5.sdk --enable-macos-target=10.5"

# Linux: Gary Kowng from 612809 comment 16
  CROSS32_L1="CC='gcc -m32' CXX='g++ -m32' AR=ar sh ../configure --target=i686-pc-linux --disable-tests --disable-optimize --enable-debug"

# Linux: Nicholas Nethercote from 608696 comment 33:
  CROSS32_L2="CC='gcc -m32' CXX='g++ -m32' AR=ar ../configure --enable-debug --enable-valgrind --disable-optimize --target=i686-pc-linux-gnu"


##############################
# Task lists
##############################

Check:
  compile, test

Quick:
  compile, jit-test, sunspider, ubench

Full:
  compile, jit-test, ref-test, sunspider, v8, ubench, build-firefox, dump-patch

##############################
# Building
##############################
compile(DIR=OBJDIR_OPT, CONFIGURE_FLAGS="--enable-optimize --disable-debug"):
  possibly_configure (DIR, CONFIGURE_FLAGS)
  RETVAL=$ @MAKE -C @DIR

compile_debug(DIR=OBJDIR_DBG):
  RETVAL=compile (DIR, "--enable-debug --disable-optimize")

compile_njn(DIR=OBJDIR_NJN):
  RETVAL=compile (DIR, "--enable-optimize --disable-debug --enable-debug-symbols")


possibly_configure(DIR, CONFIGURE_FLAGS):
  $ test -e configure || autoconf213
  $ test -e @DIR || mkdir -p @DIR
  $ test -e @DIR/Makefile || (cd @DIR && ../configure @CONFIGURE_FLAGS --enable-threadsafe --with-system-nspr)


Build-firefox:
  $ @MAKE -f client.mk build -C ../../

Tags:
  $ ctags -R --languages=c,c++ --exclude='build_*' .


##############################
# Tests
##############################
test:
  jit-test, ref-test

jit-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  $ @MAKE -C @DIR # don't want it to configure
  $ python -u jit-test/jit_test.py @DIR/js @TEST-SPEC

ref-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  $ @MAKE -C @DIR # don't want it to configure
  $ python -u tests/jstests.py --args="-j -m" @DIR/js @TEST-SPEC


##############################
# Benchmarks
##############################
bench(DIR, SUITE, RUN_COUNT, EXTRA_COMMAND=""):
  print ("Running the suite: @SUITE")
  OUTPUT=$ cd SunSpider && perl ./sunspider --args="-j -m" --shell=@DIR/js --run=@RUN_COUNT --suite=@SUITE @EXTRA_COMMAND

# Rename the results file to include the branch.
  OLDFILE=$ echo "@OUTPUT" | tail -n 1 | sed 's/Results are located at //'
  BASE=$ basename @OLDFILE
  DATE=$ echo @BASE | sed 's/sunspider-results-//' | sed 's/\.js$//'
  NEWFILE="@SUITE\-results/@BRANCH\-@DATE.js"
  $ mv SunSpider/@OLDFILE SunSpider/@NEWFILE

  RETVAL="@NEWFILE" # TODO: there is an error if I sat X=Y, fix it.


Baseline: # run the benchmarks after popping all the directories
  PATCHNAME=$ hg qtop
  $ hg qgoto baseline
# Compile the different types we need later
  compile (OBJDIR_BASELINE_OPT)
  compile_debug (OBJDIR_BASELINE_DBG)
  compile_njn (OBJDIR_BASELINE_NJN)
# Run the benchmarks for later comparisons
  RESULT_FILE1 = baseline_bench ("sunspider-0.9.1", "150")
  RESULT_FILE2 = baseline_bench ("v8-v6", "75")
  RESULT_FILE3 = baseline_bench ("ubench", "150")
  $ hg qgoto @PATCHNAME
  RETVAL="@RESULT_FILE1\n@RESULT_FILE2\n@RESULT_FILE3\n"

baseline_bench(TEST, COUNT):
  RETVAL= bench (OBJDIR_BASELINE_OPT, "@TEST", "@COUNT", "--set-baseline")
  $ echo "@RETVAL" > SunSpider/@TEST\-results/baseline-filename.txt


ss_harness_compare(SUITE, FILE1, FILE2, DIR):
  RETVAL=$ cd Sunspider && perl ./sunspider-compare-results --suite @SUITE @FILE1 @FILE2  --shell @DIR/js

ss_harness_bench(DIR, SUITE, COUNT):
  compile(DIR)
  FILE1=$ cat SunSpider/@SUITE\-results/baseline-filename.txt
  FILE2=bench(DIR, "@SUITE", "@COUNT")
  RETVAL=ss_harness_compare(SUITE, FILE1, FILE2, DIR)
  

sunspider(DIR=OBJDIR_OPT):
  RETVAL=ss_harness_bench(DIR, "sunspider-0.9.1", "100")

v8(DIR=OBJDIR_OPT):
  RETVAL=ss_harness_bench(DIR, "v8-v6", "30")

ubench(DIR=OBJDIR_OPT):
  RETVAL=ss_harness_bench(DIR, "ubench", "30")


##############################
# Valgrind
##############################

njn(DIR1=OBJDIR_BASELINE_NJN, DIR2=OBJDIR_NJN):
  compile_njn
# these would be better if I also included --enable-debug-symbols
  print ("I can't make this work. In your shell:")
  print ("  source ~/vcs/mozilla/njn.sh")
  print ("  ss_cmp_cg @DIR1 @DIR2")
  print ("  v8_cmp_cg @DIR1 @DIR2")
  print ("  ub_cmp_cg @DIR1 @DIR2")
  


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
  $ hg --cwd @DIR qimport -P ../sunspider.patch
  $ hg --cwd @DIR qimport -P ../single_apply.patch
  $ hg --cwd @DIR qnew baseline

fetch:
  PARENT=$ hg showconfig | grep paths\.default= | sed 's/paths.default=//'
  $ hg fetch --cwd @PARENT
  $ hg fetch

tmhgurl:
  REV=$ hg identify -i
  RETVAL = "http://hg.mozilla.org/tracemonkey/rev/@REV"

disfile(FILENAME):
  RETVAL=$ @OBJDIR_DBG/js -e 'disfile("-r", "-l", "@FILENAME")'


##########################
# Shell cross-compile
##########################

mac32:
  test_full_cross_compile(CROSS32_O1, "1")
  test_full_cross_compile(CROSS32_O2, "2")
  test_full_cross_compile(CROSS32_O3, "3")
  test_full_cross_compile(CROSS32_O4, "4")
  test_full_cross_compile(CROSS32_O5, "5")

linux32:
  test_full_cross_compile(CROSS32_L1, "1")
  test_full_cross_compile(CROSS32_L2, "2")

test_full_cross_compile(COMMAND, NUMBER):
  test_cross_compile(COMMAND, "@NUMBER\_p", "")
  test_cross_compile(COMMAND, "@NUMBER\_d", "--disable-optimize --enable-debug")
  test_cross_compile(COMMAND, "@NUMBER\_o", "--enable-optimize --disable-debug")

test_cross_compile(COMMAND, NUMBER, EXTRAS):
  DIR="build_shell_@NUMBER\_DBG.OBJ"
  $ autoconf213
  $ rm -Rf @DIR
  $ mkdir -p @DIR
# buggery parser HACK
  $(DIR) (cd @DIR && @COMMAND @EXTRAS)
  RETVAL=$ @MAKE -C @DIR



