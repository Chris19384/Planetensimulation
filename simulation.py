"""
    Module to send changing object positions through a pipe.

    bodies is a numpy array which has the following structure:
    [
        [x, y, z, radius(scale)],
        [x, y, z, radius(scale)]
    ]

    this bodies array is gonna be sent into the receiver pipe
    m8 you there bro?



# T O D O:
#  - GUI elements:
#    - show last momentum
#    - switch for multiple possible rotations / 3 dimensions (initial speed)
#    - disable certain GUI elements when simulation started
#    - change scale while simulation running
#  - implement fps change in renderer (another pipe?)
#  - rename Cython implementation (e.g. worker_distributed) (how is it done?)
#  - more documentation

"""


# libs
import cProfile
import copy
import io
import pstats
import random
import time
from importlib import import_module
import numpy as np
import lib.umsgpack as umsgpack

# my libs
from lib.helper import valueMap, time_ms, get_log_func
from lib.planet_helper import load_planets, save_planets, calc_impulse, calc_initial_speed, calc_point_mass_for_planet
from config import Config
from planets import Planets
from simulation_constants import END_MESSAGE
from distributed_master import DistributedMaster


log = get_log_func("[simu]")
worker = None

config = None

# debug options (GET SET VIA CONFIG)
DEBUG_PLANETS = False
DEBUG_FPS = False
DEBUG_MOMENTUM = True



_TYPE = np.float64
random_directions = [
    np.array([1, 0, 1], dtype=_TYPE),
    np.array([0, 1, 1], dtype=_TYPE),
    np.array([1, 1, 0], dtype=_TYPE),
]


def _initialise_planets(nr_of_planets: int):
    """

    :param nr_of_planets:
    :return: a planets object containing the specified amount of planets
    """

    # get mode from config
    mode = config.mode_stuff["modes"][config.mode_stuff["mode"]]

    # load up planets from file if needed
    if mode == "last planet data":
        pl, mode, success = load_planets(config.load_planets_file)
        if not success:
            log("FATAL: could not load file", config.load_planets_file)
            log("File Error. Fallback to 'real' mode...")
            config.mode = "real"
            return _initialise_planets(nr_of_planets)
        log("pl", pl)

        # overwrite mode with the mode the data had
        config.mode = mode

        return pl

    # randomly generate planets
    elif mode == "random":

        # planets obj
        planets: Planets = Planets(nr_of_planets + 1)

        # set blackhole
        planets.pos[0] = np.array((0, 0, 0), dtype=np.float64)
        planets.masses[0] = config.b_hole_default_mass
        planets.radii[0] = config.b_hole_default_radius
        planets.speeds[0] = np.array((0, 0, 0), dtype=np.float64)
        planets.accels[0] = np.array((0, 0, 0), dtype=np.float64)
        planets.names[0] = "B L A C K H O L E"

        # fill planet data (pos, mass, radius, speed, accel)
        for i in range(1, nr_of_planets + 1):

            # gen random positions for initializing
            # loop for planets not to spawn to close to the sun
            pos = np.array((0, 0, 0), dtype=np.float64)
            while np.linalg.norm(pos) < 0.01:
                rnd_x = random.uniform(-1, 1)
                rnd_y = random.uniform(-1, 1)
                rnd_z = random.uniform(-1, 1)
                pos = np.array((rnd_x, rnd_y, rnd_z), dtype=np.float64)
                rnd_scale = random.uniform(config.dist_to_sun_min, config.dist_to_sun_max)
                pos *= rnd_scale

            # gen random mass
            mass = random.uniform(config.mass_min, config.mass_max)

            # gen random radius
            radius = valueMap(mass, config.mass_min, config.mass_max, config.radius_min, config.radius_max)

            # set vals
            planets.pos[i] = pos
            planets.masses[i] = mass
            planets.radii[i] = radius

        for i in range(1, nr_of_planets + 1):

            # calculate point mass and point mass position for that planet
            point_mass, r_s_l = calc_point_mass_for_planet(i, planets)
            planets.speeds[i] = calc_initial_speed(planets.pos[i], planets.masses[i], point_mass, r_s_l)

        return planets

    # or emulate the real sunsystem
    elif mode == "real":

        # planets obj
        planets: Planets = Planets(len(config.planets))

        planets_in_config = config.planets_data
        for i, name_planet in enumerate(planets_in_config.items()):

            # unpack
            name = name_planet[0]
            planet = name_planet[1]

            # gen a position
            # arbitrary point on a circle
            # x^2 + y^2 = 1
            # sqrt(1 - x^2) = y
            x = np.array((random.uniform(-1, 1)), dtype=np.float64)
            y = np.sqrt(1 - x ** 2)

            # scale
            x *= planet["distanceToSun"]
            y *= planet["distanceToSun"]

            # set planet
            planets.pos[i] = np.array((x, y, 0.0), dtype=np.float64)
            planets.masses[i] = planet["mass"]
            planets.radii[i] = planet["radius"]
            planets.speeds[i] = np.array((0, 0, 0), dtype=np.float64)
            planets.accels[i] = np.array((0, 0, 0), dtype=np.float64)
            planets.names[i] = name

        # expect the first one to be the sun
        for i in range(1, planets.n):

            # calculate point mass and point mass position for that planet
            point_mass, r_s_l = calc_point_mass_for_planet(i, planets)

            # set speed
            planets.speeds[i] = calc_initial_speed(planets.pos[i], planets.masses[i], point_mass, r_s_l)

        return planets

    # no mode that is supported
    else:
        raise AssertionError(f"mode {mode} is not supported!")





def startup(sim_pipe, sim_config: Config):
    """
    Initialise and continuously update a position list.

    Results are sent through a pipe after each update step
    :param sim_pipe:
    :param sim_config:
    :return:
    """

    global config
    global worker
    global chunks
    global DEBUG_PLANETS, DEBUG_FPS, DEBUG_MOMENTUM, DEBUG_CLUSTER_TIMES, DEBUG_CLUSTER_RESULT

    # assign config
    config = sim_config
    assert config

    # set all debug options
    DEBUG_PLANETS = config.debug["planets"]
    DEBUG_FPS = config.debug["sim_fps"]
    DEBUG_MOMENTUM = config.debug["momentum"]

    cluster_active = config.cluster["active"]
    dmaster: DistributedMaster = None

    # check for cluster use
    # and init if necessary
    if cluster_active:
        dmaster = DistributedMaster(config)
        if dmaster.is_healthy():
            log("DistributedMaster ok")
        else:
            log("DistributedMaster FAILED")
    else:
        # load specific update implementation
        try:
            worker = import_module("native." + config.update_impl)
            log("  OK:")
            log(f"      update implementation {config.update_impl} loaded")
        except Exception:
            log(" !-_Error_-! importing update implementation", config.update_impl)
            log(f"     Falling back to fallback impl {config.update_impl_fallback}")
            worker = import_module("native.worker_01")

    # init vars
    x_runner = 0
    paused = False

    # cache vars
    delta_t = sim_config.delta_t
    print_every = sim_config.print_every

    # time that one simulation step should take
    # in ms
    max_step_ms = 1000 / sim_config.sim_fps

    # load planets
    planets: Planets = _initialise_planets(int(config.nr_planets))
    log("Planets after initialization (startup(), _initialise_planets()): ", planets)

    while True:

        t1 = time_ms()

        if sim_pipe.poll():
            message = sim_pipe.recv()
            if isinstance(message, str) and message == END_MESSAGE:
                if message == END_MESSAGE:
                    if cluster_active:
                        dmaster.cleanup(planets)
                        pass
                    log('exiting ...')
                    break
                else:
                    log("received message:", message)
            elif isinstance(message, dict):
                if "chunks" in message:
                    # log(f"change chunks called: {message['chunks']}")
                    chunks = message['chunks']
                if "fps" in message:
                    log("change fps called: ", message["fps"])
                    max_step_ms = 1000 / message["fps"]
                elif "delta_t" in message:
                    log("change delta_t called: ", message["delta_t"])
                    delta_t = message["delta_t"]
                elif "paused" in message:
                    log("change paused called: ", message["paused"])
                    paused = message["paused"]
                elif "save_planets" in message:
                    log("save_planets called", message["save_planets"])
                    save_planets(planets, config.mode_stuff["mode"], filename=message["save_planets"])
                continue

        if not paused:

            ###
            # perform simulation step
            ###

            new_planets: Planets = copy.deepcopy(planets)

            # perform step (in-memory)
            t_worker_start = time_ms()
            if cluster_active:
                dmaster.calculate_planets(planets, new_planets, delta_t)
            else:
                worker.move_planets(planets.pos, planets.speeds, planets.accels, planets.masses, new_planets.pos,
                                    new_planets.speeds, new_planets.accels, planets.n, delta_t)
            t_worker = time_ms() - t_worker_start

            # convert to a renderable format and send to the receiver
            # send to receiver process
            t_renderable_start = time_ms()
            renderable = planets.pos_to_renderable_numpy_array(config.scale_factor_world[str(config.mode_stuff["mode"])],
                                              config.scale_factor_planet[str(config.mode_stuff["mode"])])
            t_renderable = time_ms() - t_renderable_start

            # send to receiver (should be renderer)
            t_send_start = time_ms()
            sim_pipe.send_bytes(umsgpack.packb(renderable))
            t_send = time_ms() - t_send_start

            # update bodies
            planets = new_planets

            # every <print_every> output some status
            if x_runner % print_every == 0:
                if DEBUG_MOMENTUM:
                    # log(f"loop step: {time_ms() - t1}ms, {x_runner}x")
                    log(f"momentum: {calc_impulse(planets):0.0f}")
                if DEBUG_PLANETS:
                    log("planets:", planets)
            x_runner = x_runner + 1

            # wait for fps if necessary
            t = time_ms() - t1
            if t < max_step_ms:
                time.sleep((max_step_ms - t) / 1000)
            else:
                if DEBUG_FPS:
                    log()
                    log(f" - CANNOT HOLD FPS - ")
                    log(f" worker:     {t_worker}")
                    log(f" renderable: {t_renderable}")
                    log(f" send:       {t_send}")
                    log(f"{t}ms / {max_step_ms}ms")
                    log()
        else:
            time.sleep(0.05)


def startup_profile(sim_pipe, sim_config: Config):
    pr = cProfile.Profile()
    pr.enable()

    startup(sim_pipe, sim_config)

    pr.disable()
    s = io.StringIO
    sortby = 'cumulative'
    stats = pstats.Stats(pr, stream=s).sort_stats(sortby)
    stats.dump_stats(sim_config.profile_file)
    # cProfile.runctx('startup(sim_pipe, sim_config)', globals(), locals(), filename=None)
