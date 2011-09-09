#!/usr/bin/env bugger

##############################
# startup is always called
##############################
startup:
# TODO: assert we're in the right directory
  PWD=$ pwd
  BRANCH=$ hg qtop | sed 's/no patches applied/baseline/'
  OBJDIR_OPT="@PWD/objdir.OPT"
  OBJDIR_DBG="@PWD/objdir.DBG"
  OBJDIR_NJN="@PWD/objdir.NJN"
  OBJDIR_OPT_32="@PWD/objdir.OPT.32"
  OBJDIR_DBG_32="@PWD/objdir.DBG.32"
  OBJDIR_NJN_32="@PWD/objdir.NJN.32"
  OBJDIR_BASELINE_OPT="@PWD/objdir_baseline.OPT"
  OBJDIR_BASELINE_DBG="@PWD/objdir_baseline.DBG"
  OBJDIR_BASELINE_NJN="@PWD/objdir_baseline.NJN"
  MAKE="make -j2"

# OSX: Gary Kwong from 612809 comment 1
  CROSS32_O1 = "CC='gcc-4.2 -arch i386' CXX='g++-4.2 -arch i386' HOST_CC='gcc-4.2' HOST_CXX='g++-4.2' RANLIB=ranlib AR=ar AS=$CC LD=ld STRIP='strip -x -S' CROSS_COMPILE=1 ../configure --target=i386-apple-darwin8.0.0 --enable-debug --disable-optimize --disable-tests"

# OSX: Boris Zbarsky from 612809 comment 17
  CROSS32_O2="env CC='gcc-4.2 -arch i386' CXX='g++-4.2 -arch i386' AR=ar CROSS_COMPILE=1 ../configure --enable-optimize --disable-debug --target=i386-apple-darwin9.2.0 --enable-macos-target=10.5"

# OSX: Nicholas Nethercote by email
  CROSS32_O3="CC='gcc -m32' CXX='g++ -m32' AR=ar ../configure --enable-debug --disable-optimize --target=i386-darwin"

# OSX: From MOZCONFIG via browser build
  CROSS32_O4="CC='ccache gcc-4.2 -arch i386' CXX='ccache g++-4.2 -arch i386' ../configure  --enable-application=browser --host=x86_64-apple-darwin10.4.0 --target=i386-apple-darwin9.2.0 --with-macos-sdk=/Developer/SDKs/MacOSX10.5.sdk --enable-macos-target=10.5 --enable-threadsafe --enable-ctypes --with-system-nspr"

# OSX: Minimum that should work
  CROSS32_O5="../configure --target=i386-apple-darwin9.2.0 --with-macos-sdk=/Developer/SDKs/MacOSX10.5.sdk --enable-macos-target=10.5 --enable-ctypes"

# Linux: Gary Kowng from 612809 comment 16
  CROSS32_L1="CC='gcc -m32' CXX='g++ -m32' AR=ar sh ../configure --target=i686-pc-linux --disable-tests --disable-optimize --enable-debug"

# Linux: Nicholas Nethercote from 608696 comment 33:
  CROSS32_L2="CC='gcc -m32' CXX='g++ -m32' AR=ar ../configure --enable-debug --enable-valgrind --disable-optimize --target=i686-pc-linux-gnu"


##############################
# Task lists
##############################

Check:
  compile_debug, jit-test

Quick:
  compile_opt, jit-test, sunspider, ubench

Full:
  compile_opt, compile_debug, jit-test, ref-test, sunspider, v8, ubench, build-firefox, export 

##############################
# Building
##############################
compile(DIR=OBJDIR_OPT, CONFIGURE_FLAGS, BIT32="0"):
  CONFIGURE_FLAGS="@CONFIGURE_FLAGS --disable-disable-compile-environment --enable-threadsafe --with-sync-build-files=@PWD/../../"
  possibly_configure (DIR, CONFIGURE_FLAGS, BIT32)
  RETVAL=$ @MAKE -C @DIR

compile_debug(DIR=OBJDIR_DBG, CONFIGURE_FLAGS=""):
  RETVAL=compile (DIR, "--enable-debug --disable-optimize --with-system-nspr @CONFIGURE_FLAGS")

compile_opt (DIR=OBJDIR_OPT, CONFIGURE_FLAGS=""):
  RETVAL=compile(DIR, "--enable-optimize --disable-debug --enable-debug-symbols --with-system-nspr @CONFIGURE_FLAGS")

compile_debug_32(DIR=OBJDIR_DBG_32, CONFIGURE_FLAGS=""):
  RETVAL=compile (DIR, "--enable-debug --disable-optimize @CONFIGURE_FLAGS", "1")

compile_opt_32(DIR=OBJDIR_OPT_32, CONFIGURE_FLAGS=""):
  RETVAL=compile(DIR, "--enable-optimize --disable-debug --enable-debug-symbols @CONFIGURE_FLAGS", "1")


#compile_njn(DIR=OBJDIR_NJN, CONFIGURE_FLAGS):
#  RETVAL=compile_opt(DIR, "--enable-optimize --disable-debug --enable-debug-symbols")


possibly_configure(DIR, CONFIGURE_FLAGS, BIT32):
  $ autoconf213
  CC=$ test 1 -eq @BIT32 && echo 'CC="ccache gcc-4.2 -arch i386" CXX="ccache g++-4.2 -arch i386" CROSS_COMPILE=1' || echo ''
  $ test -e @DIR || mkdir -p @DIR
  $ test -e @DIR/Makefile || (cd @DIR && @CC ../configure @CONFIGURE_FLAGS)


Build-firefox:
  $ @MAKE -f client.mk build -C ../../

Tags:
  $ ctags -R --languages=c,c++ --exclude='objdir*' --exclude='jsprvtd.h' .


##############################
# Tests
##############################
test:
  jit-test, ref-test

valgrind-jit-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  $ @MAKE -C @DIR # don't want it to configure
  $ python -u jit-test/jit_test.py @DIR/js --valgrind --jitflags=jmp @TEST-SPEC

jit-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  $ @MAKE -C @DIR # don't want it to configure
  $ python -u jit-test/jit_test.py @DIR/js --jitflags=,m,j,mj,mjp,mjd @TEST-SPEC

ref-test(TEST-SPEC="", DIR=OBJDIR_DBG):
  $ @MAKE -C @DIR # don't want it to configure
  $ LC_TIME=en_US.UTF-8 python -u tests/jstests.py --args="-jmp" @DIR/js @TEST-SPEC


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

Rebase:
  PATCHNAME=$ hg qtop
  $ hg qpop -a
  fetch
  $ hg qgoto @PATCHNAME

Baseline: # run the benchmarks after popping all the directories
  PATCHNAME=$ hg qtop
  $ hg qgoto baseline
# Compile the different types we need later
  compile (OBJDIR_BASELINE_OPT)
  compile_debug (OBJDIR_BASELINE_DBG)
#  compile_njn (OBJDIR_BASELINE_NJN)
# Run the benchmarks for later comparisons
  RESULT_FILE1 = baseline_bench ("sunspider-0.9.1", "150")
  RESULT_FILE2 = baseline_bench ("v8-v4", "75")
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
  RETVAL=ss_harness_bench(DIR, "v8-v4", "30")

ubench(DIR=OBJDIR_OPT):
  RETVAL=ss_harness_bench(DIR, "ubench", "30")


##############################
# Valgrind
##############################

#njn(DIR1=OBJDIR_BASELINE_NJN, DIR2=OBJDIR_NJN):
#  compile_njn
#  print ("I can't make this work. In your shell:")
#  print ("  source ~/vcs/mozilla/njn.sh")
#  print ("  ss_cmp_cg @DIR1 @DIR2")
#  print ("  v8_cmp_cg @DIR1 @DIR2")
#  print ("  ub_cmp_cg @DIR1 @DIR2")
  


##############################
# Utils
##############################
export:
  $ hg export qbase:@BRANCH > ~/work/mozilla/@BRANCH.patch

newclone(DIR, PARENT_DIR="clean-mozilla-central"):
  $ hg fetch --cwd @PARENT_DIR
  $ hg clone @PARENT_DIR @DIR
  PARENT=hg_parent(PARENT_DIR)
  $ echo "default-push = ssh@PARENT" >> @DIR/.hg/hgrc
  $ hg --cwd @DIR qinit -c 

hg_parent(DIR):
  RETVAL=$ hg --cwd @DIR showconfig | grep paths\.default= | sed 's/paths.default=https//' | sed 's/paths.default=http//' | sed 's/paths.default=//'
  

fetch:
  PARENT=hg_parent(PWD)
  $ hg fetch --cwd @PARENT
  $ hg fetch

tmhgurl:
  REV=$ hg identify -i
  RETVAL = "http://hg.mozilla.org/mozilla-central/rev/@REV"

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



