Tiny introduction
==============================

Buggery is a domain specific language for short command-driven scripts.  It is
designed for simplicity and maintainability, and aims at the niche where
Python, bash and make are nearly but not quite the right tools. 

Longer introduction
==============================

In every project, someone starts to script something in bash. They should
really have used Python, but bash is easier to get started with. After a few
weeks and months, their shell script has grown to epic proportions, it has
become hard to maintain, and they wish they had written it in Python after all.
On numerous occasions, a colleague asks for the script, deems it too difficult
to understand and maintain, and writes their own. They think they should use
Python, but bash is easier to get started with...

Buggery is a domain specific language for command-line scripts, designed to
replace shell scripting. It is designed for simplicity and maintainability,
which are the real problems with shell scripts. It aims at the niche where
Python, bash and make are nearly but not quite the right tools. 

Here is a simple buggery script, saved in `~/bin/go`:

    #!/usr/bin/env bugger 

    Quick:
      compile, test, bench

    compile:
      $ make -C build/

    test:
      $ python tests/unit-test --all

    bench:
      $ make -C build/ benchmark
      $ build/benchmark --compare-to build/baseline-test-results.txt

At the command line, use it by running:

    go quick

This runs the 'Quick' task, which runs the 'compile' and 'test' tasks.


Contact
==============================

Written by Paul Biggar, send all bugs to him (paul.biggar@gmail.com).

You can also use the issue tracker or send pull requests using github (http://github.com/pbiggar/buggery).
