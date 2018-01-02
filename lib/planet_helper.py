import numpy as np
import pickle

from lib import umsgpack
from planets import Planets



Z_COORD = np.array((0, 0, 1), dtype=np.float64)
G = 6.67408e-11


def load_planets(filename):
    """

    :param filename:
    :return: (planets object, mode, success)
    """

    raw = ""
    try:
        with open(filename, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, None, False

    # parse
    d = umsgpack.unpackb(raw)
    #print("raw:", raw)
    #print("type(raw):", type(raw))

    planets = Planets(1)
    planets.deserialize(d["planets"])
    mode = int(d["mode"])

    return planets, mode, True


def save_planets(planets, mode, filename):
    """

    :param planets:
    :param filename:
    :return: success
    """

    d = dict()
    d.update({
        "planets": planets.serialize(),
        "mode": int(mode)
    })

    try:
        with open(filename, "wb") as f:
            f.write(umsgpack.packb(d))
    except FileNotFoundError:
        return False

    return True


def serialize_np(arr: np.ndarray):
    return pickle.dumps(arr, protocol=0)

def deserialize_np(str) -> np.ndarray:
    return pickle.loads(str)




###
# Planets Math
###

def calc_impulse(planets: Planets):
    """
    calculate the impulse of all Planets
    the returned value should always stay the same
    while the simulation is running
    """
    imp = 0
    for i, mass in enumerate(planets.masses):
        imp += mass * planets.speeds[i]

    return np.linalg.norm(imp)


# do NOT count the current planet when calculating the point mass
# this will probably mess up the initial speed
def calc_point_mass_for_planet(index: int, planets: Planets):
    """

    :param planets:
    :return: the point mass M and its position r_s
    """

    M = 0

    # sum of all m_i * r_i without planet at index
    mass_pos_sum = 0
    for i, mass in enumerate(planets.masses):
        if i != index:
            M += mass
            mass_pos_sum += mass * planets.pos[i]

    # position
    r_s_l = mass_pos_sum / M

    return (M, r_s_l)


def calc_initial_speed(planet_positition: np.array, planet_mass, bulk_mass, bulk_position: np.array):
    """
    initial SPEED calculation for each planet goes here
    :param planet_positition:
    :param planet_mass: mass of the planet
    :param bulk_position: position of point mass?
    :param bulk_mass: mass of ALL other planets (point mass?)
    :return: numpy array (x,y,z) inital speed vector for this planet
    """

    # calculate length of vector planet <-> bulk
    r_i = planet_positition
    r_si = bulk_position
    r = np.linalg.norm(r_i - r_si)

    M = bulk_mass
    m_i = planet_mass

    # calculate abs speed of our planet
    abs_v_i = ((M - m_i) / M) * np.sqrt((G * M) / r)

    # calculate direction of the speed
    # random.choice(random_directions)
    dotted = np.cross(r_i - r_si, Z_COORD)#random.choice(random_directions)) # Z_COORD
    v_i = dotted / np.linalg.norm(dotted)

    # divide v_i by its length to norm it
    v_i /= np.linalg.norm(v_i)

    # stretch v_i by abs_vi
    v_i = v_i * abs_v_i

    # return optimal speed vector of this planet
    return v_i





if __name__ == '__main__':
    p, suc = load_planets('planets.msgpack')
    for pl in p: print(pl)
