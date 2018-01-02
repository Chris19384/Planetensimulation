cimport cython
from cython.parallel import parallel, prange

from libc.math cimport sqrt
from libc.stdlib cimport malloc, calloc, free
from libc.stdio cimport printf
from libc.string cimport memset

import numpy as np
cimport numpy as np

cdef double G = 6.67408e-11


# TODO fix this one
@cython.cdivision(True)
@cython.boundscheck(False) # turn off bounds-checking for entire function
def move_planets(np.ndarray o_positions,
                        np.ndarray o_speeds,
                        np.ndarray o_accels,
                        np.ndarray o_masses,
                        np.ndarray n_positions,
                        np.ndarray n_speeds,
                        np.ndarray n_accels,
                        num_planets,
                        delta_t):
    """
    o_* represent old planet data
    n_* represent the planet data we write into
    :param o_positions:
    :param o_speeds:
    :param o_accels:
    :param o_masses:
    :param n_positions:
    :param n_speeds:
    :param n_accels:
    :param num_planets:
    :return:
    """

    cdef long i = 0
    cdef long j = 0

    # get memory views on numpy arrays
    cdef double [:, :] p_o_pos = o_positions
    cdef double [:, :] p_o_speeds = o_speeds
    cdef double [:, :] p_o_accels = o_accels
    cdef double [:, :] p_o_masses = o_masses
    cdef double [:, :] p_n_pos = n_positions
    cdef double [:, :] p_n_speeds = n_speeds
    cdef double [:, :] p_n_accels = n_accels

    # temporary vars (READ-ONLY)
    cdef double delta_t_fast = delta_t
    cdef double delta_t_sq_half = ((delta_t_fast ** 2) / 2)
    cdef long num_planets_fast = num_planets

    # kick away gil
    with nogil:

        # this loop is mostly thread-local
        # writes to the specific planet data address
        for i in prange(num_planets_fast, schedule='static'):

            v = <double *> calloc(3, sizeof(double))
            abs_dist_planets = <double *> calloc(1, sizeof(double))
            p_resulting_force = <double *> calloc(3, sizeof(double))

            for j in range(num_planets_fast):

                if i != j:

                    # faster norm impl:
                    v[0] = p_o_pos[j, 0] - p_o_pos[i, 0]
                    v[1] = p_o_pos[j, 1] - p_o_pos[i, 1]
                    v[2] = p_o_pos[j, 2] - p_o_pos[i, 2]

                    abs_dist_planets[0] = sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)

                    p_resulting_force[0] += G * ((p_o_masses[i, 0] * p_o_masses[j, 0]) / (abs_dist_planets[0] ** 3)) * v[0]
                    p_resulting_force[1] += G * ((p_o_masses[i, 0] * p_o_masses[j, 0]) / (abs_dist_planets[0] ** 3)) * v[1]
                    p_resulting_force[2] += G * ((p_o_masses[i, 0] * p_o_masses[j, 0]) / (abs_dist_planets[0] ** 3)) * v[2]


            accel = <double *> calloc(3, sizeof(double))
            pos = <double *> calloc(3, sizeof(double))
            speed = <double *> calloc(3, sizeof(double))

            accel[0] = p_resulting_force[0] / p_o_masses[i, 0]
            accel[1] = p_resulting_force[1] / p_o_masses[i, 0]
            accel[2] = p_resulting_force[2] / p_o_masses[i, 0]

            pos[0] = p_o_pos[i, 0] + delta_t_fast * p_o_speeds[i, 0] + delta_t_sq_half * p_o_accels[i, 0]
            pos[1] = p_o_pos[i, 1] + delta_t_fast * p_o_speeds[i, 1] + delta_t_sq_half * p_o_accels[i, 1]
            pos[2] = p_o_pos[i, 2] + delta_t_fast * p_o_speeds[i, 2] + delta_t_sq_half * p_o_accels[i, 2]

            speed[0] = p_o_speeds[i, 0] + accel[0] * delta_t_fast
            speed[1] = p_o_speeds[i, 1] + accel[1] * delta_t_fast
            speed[2] = p_o_speeds[i, 2] + accel[2] * delta_t_fast

            # set new vals
            # this is where non-thread-local access happens
            p_n_pos[i, 0] = pos[0]
            p_n_pos[i, 1] = pos[1]
            p_n_pos[i, 2] = pos[2]

            p_n_accels[i, 0] = accel[0]
            p_n_accels[i, 1] = accel[1]
            p_n_accels[i, 2] = accel[2]

            p_n_speeds[i, 0] = speed[0]
            p_n_speeds[i, 1] = speed[1]
            p_n_speeds[i, 2] = speed[2]

            free(v)
            free(abs_dist_planets)
            free(p_resulting_force)
            free(accel)
            free(pos)
            free(speed)

