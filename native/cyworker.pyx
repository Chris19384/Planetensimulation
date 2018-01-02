
"""
# c_ython: profile=True
# c_ython: linetrace=True
this should be the distributed worker function
highly unstable right now
also, cyworker_parallel is waay faster than this
"""

cimport cython
import cython
from cython.parallel cimport parallel, prange
cimport openmp

from libc.math cimport sqrt, lround
from libc.stdlib cimport malloc, calloc, free
from libc.stdio cimport printf
from libc.string cimport memset

import numpy as np
cimport numpy as np

cdef double G = 6.67408e-11
cdef long CHUNKS = openmp.omp_get_num_threads()*2


#@cython.profile(True)
@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.initializedcheck(False)
@cython.nonecheck(False)
def update_planet_indices(np.ndarray o_positions,
                        np.ndarray o_speeds,
                        np.ndarray o_accels,
                        np.ndarray o_masses,
                        num_planets,
                        i_from_,
                        i_to_,
                        delta_t):
    """
    Update one planet's values (n_* arrays at position index_to_update)
    Provide all planet data in o_* variables
    :param o_positions:
    :param o_speeds:
    :param o_accels:
    :param o_masses:
    :param num_planets:
    :param i_from: inclusive
    :param i_to:   exclusive
    :param delta_t:
    :return:
    """

    # indices
    cdef long i = 0
    cdef long j = 0
    cdef long k = 0
    cdef long dim = 0

    # memory views on numpy arrays
    cdef double [:, :] p_o_pos = o_positions
    cdef double [:, :] p_o_speeds = o_speeds
    cdef double [:, :] p_o_accels = o_accels
    cdef double [:, :] p_o_masses = o_masses

    # temporary vars (READ-ONLY)
    cdef double delta_t_fast = delta_t
    cdef double delta_t_sq_half = ((delta_t_fast ** 2) / 2)
    cdef long num_planets_fast = num_planets
    cdef long i_from = i_from_
    cdef long i_to = i_to_
    cdef long span = i_to - i_from
    cdef long _offset = 0

    # thread _local_ vars
    cdef double abs_dist_planets = 0
    cdef double tmp = 0
    cdef double v0 = 0
    cdef double v1 = 0
    cdef double v2 = 0

    # the arrays we will write into
    r_pos = np.empty((span, 3), dtype=np.float64)
    r_speeds = np.empty((span, 3), dtype=np.float64)
    r_accels = np.empty((span, 3), dtype=np.float64)
    cdef double [:, :] p_r_pos = r_pos
    cdef double [:, :] p_r_speeds = r_speeds
    cdef double [:, :] p_r_accels = r_accels


    # TODO does parallel() improve anything?
    with nogil, parallel():

        # thread _local_ pointers / buffers
        p_resulting_force = <double *> calloc(3, sizeof(double))
        forces = <double *> malloc(3 * num_planets_fast * sizeof(double))

        # loop over the span of planets
        for _offset in prange(span, schedule='static'):
        #for _offset in range(span):
            i = i_from + _offset

            # loop over all other planets (to calc the force to them)
            for j in range(num_planets_fast):

                if i != j:
                    #printf("i=%ld, j=%ld\n", i, j)
                    v0 = p_o_pos[j, 0] - p_o_pos[i, 0]
                    v1 = p_o_pos[j, 1] - p_o_pos[i, 1]
                    v2 = p_o_pos[j, 2] - p_o_pos[i, 2]

                    abs_dist_planets = sqrt(v0 ** 2 + v1 ** 2 + v2 ** 2)

                    tmp = G * ((p_o_masses[i, 0] * p_o_masses[j, 0]) / (abs_dist_planets ** 3))

                    forces[j*3 + 0] = tmp * v0
                    forces[j*3 + 1] = tmp * v1
                    forces[j*3 + 2] = tmp * v2

                else:
                    # null out forces
                    forces[j*3 + 0] = 0
                    forces[j*3 + 1] = 0
                    forces[j*3 + 2] = 0


            # null out (to cut down artifacts of previous iteration)
            memset(p_resulting_force, 0, 3 * sizeof(double))

            # sum up vector forces to get p_resulting_force
            # and set data
            for dim in range(3):
                for k in range(num_planets_fast):
                    p_resulting_force[dim] += forces[k*3 + dim]

                p_r_accels[i-i_from, dim] = p_resulting_force[dim] / p_o_masses[i, 0]
                p_r_pos[i-i_from, dim]    = p_o_pos[i, dim] + delta_t_fast * p_o_speeds[i, dim] + delta_t_sq_half * p_o_accels[i, dim]
                p_r_speeds[i-i_from, dim] = p_o_speeds[i, dim] + p_r_accels[i-i_from, dim] * delta_t_fast


        free(p_resulting_force)
        free(forces)

    # return numpy (slices)
    return r_pos, r_speeds, r_accels


def move_planets(np.ndarray o_positions,
                        np.ndarray o_speeds,
                        np.ndarray o_accels,
                        np.ndarray o_masses,
                        np.ndarray n_positions,
                        np.ndarray n_speeds,
                        np.ndarray n_accels,
                        num_planets,
                        delta_t):

    cdef long ifrom = 0
    cdef long ito = num_planets

    r_pos, r_speeds, r_accels = update_planet_indices(o_positions, o_speeds, o_accels, o_masses, num_planets, ifrom, ito, delta_t)
    np.copyto(n_positions, r_pos)
    np.copyto(n_speeds, r_speeds)
    np.copyto(n_accels, r_accels)