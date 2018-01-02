all: compile

compile:
	python3 setup.py build_ext --inplace

perf:
	$(shell for prog in \$(basename *.pyx .pyx) ; do cython -a $$prog.pyx ; done)

showperf:
	$(shell for perffile in \$(basename *.pyx .pyx) ; do firefox $$perffile.html ; done)

jupyter:
	jupyter-notebook

specialperf:
	nothing=$(shell cd ..; python create_profile_data.py)
	python -m line_profiler ../test.lprof > results.txt

clean:
	$(shell rm -rf build/ *.html *.c *.so)
