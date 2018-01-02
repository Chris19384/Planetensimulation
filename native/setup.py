# Aufruf: python3 setup.py build_ext --inplace
# Windows: zusaetzliche Option --compiler=mingw32
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

# for line by line profiling
"""
from Cython.Compiler.Options import get_directive_defaults
directive_defaults = get_directive_defaults()
directive_defaults['linetrace'] = True
directive_defaults['binding'] = True


    Extension("cyworker", ["cyworker.pyx"],
              extra_compile_args=['-O3', '-fopenmp'], libraries=['m'],
              extra_link_args=["-fopenmp"],
              include_dirs=[numpy.get_include()],
              define_macros=[('CYTHON_TRACE_NOGIL', '1')])

"""

ext_modules=[
    Extension("cyworker_np", sources=["cyworker_np.pyx"],
              extra_compile_args=['-O3'], libraries=['m'],  include_dirs=[numpy.get_include()]),
    Extension("cyworker_optimized", sources=["cyworker_optimized.pyx"],
              extra_compile_args=['-O3'], libraries=['m'],  include_dirs=[numpy.get_include()]),
    Extension("cyworker_parallel", ["cyworker_parallel.pyx"],
              extra_compile_args=['-O3', '-fopenmp'], libraries=['m'],
              extra_link_args=["-fopenmp"],
              include_dirs=[numpy.get_include()]),
    Extension("cyworker", ["cyworker.pyx"],
              extra_compile_args=['-O3', '-fopenmp'], libraries=['m'],
              extra_link_args=["-fopenmp"],
              include_dirs=[numpy.get_include()])

]
setup( name = 'Planetensimulation',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules)