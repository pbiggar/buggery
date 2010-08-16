==============================
Introduction
==============================

In every project, someone starts to script something in bash. They should
really have used Python, but bash is easier to get started with. After a few
weeks and months, their shell script has grown to epic proportions, it has
become hard to maintain, and they wish they had written it in Python afterall.
On numerous occasions, a colleugue asks for the script, deems it too difficult
to understand and maintain, and writes their own. They think they should use
Python, but bash is easier to get started with...

Buggery is a domain specific language for command-line scripts, designed to
replace shell scripting. It is designed for simplicity and maintainability,
which are the real problems with shell scripts. It aims at the niche where
Python, Bash and Make are nearly but not quite the right tools. 

Here is a simple buggery script:

    Quick:
      compile, test, bench

    compile:
      $ cd build/ && make

    test:
      $ python ./unit-test --all

    bench:
      $ cd build/ && make benchmark
      $ build/benchmark --compare-to build/baseline-test-results.txt

At the command line, use it by running:

    bugger quick

This runs the 'Quick' task, which runs the 'compile' and 'test' tasks.



