import multiprocessing
import time

from config import Config
from simulation_constants import END_MESSAGE
from lib.helper import get_log_func
import simulation

log = get_log_func("[headless]")
SECONDS_TO_RUN = 120

# specify the mode in which the simulation is run
# to alter cluster values open appropriate json files or the GUI
MODE = 'cluster' # or '<worker_implementation>'


def main():



    # load config
    # make sure to configure it before using
    config = Config(filename="save.cfg.json")
    config.load()
    if MODE == 'cluster':
        config.cluster["active"] = True
        config.cluster["manager_host"] = "xray.informatik.fh-augsburg.de"
        config.cluster["manager_port"] = 33333
        config.cluster["redis_host"] = "xray.informatik.fh-augsburg.de"
        config.cluster["redis_port"] = 6379
        config.cluster["chunks"] = 8
    elif MODE in config.update_impls:
        config.update_impl = MODE
    else:
        log(f"no MODE '{MODE}'")


    # random planets
    config.mode_stuff["mode"] = 1

    # 5000
    config.nr_planets = 5000

    # load up simulation
    # create a pipe which solely purpose is to send commands to the simulation
    renderer_conn, simulation_conn = multiprocessing.Pipe()
    simulation_process = \
        multiprocessing.Process(target=simulation.startup,
                                args=(simulation_conn, config))
    simulation_process.start()

    # spin around and don't use the results
    t = time.time()
    while time.time() - t < SECONDS_TO_RUN:
        if renderer_conn.poll():
            renderer_conn.recv_bytes()

    renderer_conn.send(END_MESSAGE)
    time.sleep(0.1)

if __name__ == '__main__':
    main()