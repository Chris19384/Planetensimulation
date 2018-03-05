import numpy as np

G = 6.67408e-11

def move_planets(o_positions,
                        o_speeds,
                        o_accels,
                        o_masses,
                        n_positions,
                        n_speeds,
                        n_accels,
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

    i = 0
    j = 0
    delta_sq_half = ((delta_t ** 2) / 2)

    resulting_force = np.empty(3, dtype=np.float64)

    for i in range(num_planets):

        # clear force
        resulting_force[0] = 0.0
        resulting_force[1] = 0.0
        resulting_force[2] = 0.0

        for j in range(num_planets):

            if i != j:

                # faster norm impl:
                v = o_positions[j] - o_positions[i]
                abs_dist_planets = np.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
                resulting_force += G * ((o_masses[i] * o_masses[j]) / (abs_dist_planets ** 3)) * v

        # from the resulting force,
        # calculate acceleration
        # and the other data
        accel = resulting_force / o_masses[i]
        pos = o_positions[i] + delta_t * o_speeds[i] + delta_sq_half * o_accels[i]
        speed = o_speeds[i] + accel * delta_t

        n_positions[i] = pos
        n_accels[i] = accel
        n_speeds[i] = speed
