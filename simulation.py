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
from lib.helper import valueMap, time_ms, get_log_func, chunk_indices
from lib.planet_helper import load_planets, save_planets, calc_impulse, calc_initial_speed, calc_point_mass_for_planet
from lib.redis_wrapper import RedisWrapper
from config import Config
from planets import Planets
from simulation_constants import END_MESSAGE
from distributed_queue import TaskManager


log = get_log_func("[simu]")
worker = None

config = None

# debug options
DEBUG_PLANETS = False
DEBUG_FPS = False
DEBUG_MOMENTUM = False
DEBUG_CLUSTER_TIMES = True
DEBUG_CLUSTER_RESULT = False

# cluster
tm: TaskManager = None
rds: RedisWrapper = None
masses_pushed = False


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


def connect_to_manager(config):
    global tm, rds, job_queue, result_queue

    # setup redis
    # TODO error handling (connection to redis failed etc)
    try:
        rds = RedisWrapper(config.cluster["redis_host"], config.cluster["redis_port"], config.cluster["redis_secret"])
    except Exception as e:
        log("Exception while connecting to Redis:", e)
        exit(1)

    # setup connection to manager
    m_host = config.cluster["manager_host"]
    m_port = config.cluster["manager_port"]
    TaskManager.register('get_job_queue')
    TaskManager.register('get_result_queue')
    tm = TaskManager(address=(m_host, m_port), authkey=bytes(config.cluster["manager_secret"], encoding='ascii'))
    try:
        tm.connect()
        job_queue = tm.get_job_queue()
        result_queue = tm.get_result_queue()
        return True
    except Exception as e:
        log("Exception while connecting to Manager:", e)
        exit(1)
        return False


def calculate_manager(planets, new_planets, delta_t):
    global tm, rds, job_queue, result_queue, config, chunks, masses_pushed

    # first, clear out job_queue
    while not job_queue.empty():
        log()
        log(" OLD ITEM FOUND in job_queue. deleting!")
        log()
        job_queue.get()
        job_queue.task_done()

    # calculate job indices for the given chunksize
    t_start_chunk_indices = time_ms()
    index_tuples = list(chunk_indices(planets.n, chunks))
    t_chunk_indices = time_ms() - t_start_chunk_indices

    # push planet data to redis
    t_start_dict_update = time_ms()
    if not masses_pushed:
        rds.send_planets(planets.pos, planets.speeds, planets.accels, planets.masses, planets.n)
        masses_pushed = True
    else:
        rds.send_planets_wo_masses(planets.pos, planets.speeds, planets.accels, planets.n)
    t_dict_update = time_ms() - t_start_dict_update

    # distribute jobs to the waiting worker(s)
    t_start_put = time_ms()
    for tpl in index_tuples:
        job_queue.put((tpl[0], tpl[1], delta_t))
    t_put = time_ms() - t_start_put

    # block as long as result is not computed by all workers
    t_join_start = time_ms()
    job_queue.join()
    # empty up result_queue
    # queue should only contain a one per job:
    #  1
    for _ in index_tuples:
        result_queue.get()
    t_join = time_ms() - t_join_start

    if DEBUG_CLUSTER_RESULT:
        sqsum = 0

    # merge all results from redis
    # back into our data
    t_start_redis_apply = time_ms()
    t_queue = 0
    t_merge_all = 0
    for tpl in index_tuples:

        # indices
        ifrom = tpl[0]
        ito = tpl[1]

        t_queue_get: int = time_ms()

        # new: get all redis stuff in
        key_pos = str(ifrom) + str(ito) + 'pos'
        key_speeds = str(ifrom) + str(ito) + 'speeds'
        key_accels = str(ifrom) + str(ito) + 'accels'
        r_pos, r_speeds, r_accels = rds.get_np(key_pos), rds.get_np(key_speeds), rds.get_np(key_accels)
        # del redis
        rds.delete(key_pos)
        rds.delete(key_speeds)
        rds.delete(key_accels)

        # timing
        t_queue += time_ms() - t_queue_get

        # merge values in our data
        t_start_merge = time_ms()
        new_planets.pos[ifrom:ito][:] = r_pos[:][:]
        new_planets.speeds[ifrom:ito][:] = r_speeds[:][:]
        new_planets.accels[ifrom:ito][:] = r_accels[:][:]
        t_merge_all += time_ms() - t_start_merge

    t_redis_apply = time_ms() - t_start_redis_apply

    if DEBUG_CLUSTER_RESULT:
        log(f"cluster apply sum {sqsum}")

    # measure performance
    if DEBUG_CLUSTER_TIMES:
        log()
        log(f"    chunkup      : {t_chunk_indices}ms")
        log(f"    u_dict       : {t_dict_update}ms")
        log(f"    q_put        : {t_put}ms")
        log(f"    join         : {t_join}ms")
        log(f"    t_merge      : {t_merge_all}ms")
        log(f"    redis_apply  : {t_redis_apply}ms")
        log(f"      q_get      : {t_queue}ms")
        log()


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

    # assign config
    config = sim_config
    assert config

    cluster = config.cluster["active"]
    chunks = config.cluster["chunks"]

    # check for cluster use
    # and init if necessary
    if cluster:

        suc = connect_to_manager(config)
        if suc:
            log("[manager] connect to queue manager ok")
        else:
            log("[manager] connect to queue manager FAILED")
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
                    if cluster:
                        # TODO perform cluster cleanup
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
            if not cluster:
                worker.move_planets(planets.pos, planets.speeds, planets.accels, planets.masses, new_planets.pos,
                                    new_planets.speeds, new_planets.accels, planets.n, delta_t)
            else:
                calculate_manager(planets, new_planets, delta_t)
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
