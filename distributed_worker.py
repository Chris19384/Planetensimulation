from distributed_queue import TaskManager
from sys import argv, exit
import socket

from native.cyworker import update_planet_indices
from lib.redis_wrapper import RedisWrapper
from lib.helper import time_ms, get_log_func
from config import Config



# RedisWrapper instance
rds = None
log = get_log_func(" [worker]")

# config
config = Config("save.cfg.json")
REDIS_PW = config.cluster["redis_secret"]
MANAGER_PW = config.cluster["manager_secret"]




def __worker_function(job_queue):

    run_id_prev = -1
    pos = None
    speeds = None
    accels = None
    masses = None
    n = None
    masses_and_n_set = False

    # work forever
    while 1:

        # pull a task from the queue (blocking call)
        t_start_queue = time_ms()
        task = job_queue.get()
        ifrom, ito, delta_t, run_id = task
        # special job: clear
        if ifrom < 0:
            pos = None
            speeds = None
            accels = None
            masses = None
            masses_and_n_set = False
            n = None
            run_id_prev = -1
            job_queue.task_done()
            log(" <!> data cleared.")
            continue
        t_queue = time_ms() - t_start_queue


        # get planet data from redis server
        # if run_id has changed
        if run_id != run_id_prev or run_id == 0:
            t_start_redis = time_ms()
            if masses_and_n_set:
                pos, speeds, accels = rds.receive_planets_wo_masses()
            else:
                pos, speeds, accels, masses, n = rds.receive_planets()
                masses_and_n_set = True
            t_redis = time_ms() - t_start_redis
        else:
            t_redis = 0

        # result should contain a tuple of numpy arrays:
        #  (r_pos, r_speeds, r_accels, ifrom, ito)
        t_start_calc = time_ms()
        result = update_planet_indices( pos, speeds, accels, masses,
                                        n,
                                        ifrom,
                                        ito,
                                        delta_t)


        # redis send ( TODO FLUSH THIS AFTERWARDS ? )
        rds.set_np(str(ifrom) + str(ito) + "pos", result[0])
        rds.set_np(str(ifrom) + str(ito) + "speeds", result[1])
        rds.set_np(str(ifrom) + str(ito) + "accels", result[2])

        # send back a signal that this job is done
        job_queue.task_done()
        t_calc = time_ms() - t_start_calc

        # update run_id_prev
        run_id_prev = run_id

        # timing information
        log("Job [{:5d}:{:5d}], run #{}".format(ifrom, ito, run_id))
        log("  t_queue : {}ms".format(t_queue))
        log("  t_redis : {}ms".format(t_redis))
        log("  t_calc  : {}ms".format(t_calc))
        log()

def __start_worker(m):
    job_queue = m.get_job_queue()
    __worker_function(job_queue)

if __name__ == '__main__':

    # parse commandline arguments
    if len(argv) < 5:
        log('usage:', argv[0], '<manager_host> <manager_port> <redis_host> <redis_port>')
        exit(0)
    manager_host = argv[1]
    manager_port = int(argv[2])
    redis_host   = argv[3]
    redis_port   = int(argv[4])

    log("Manager: {}:{}".format(manager_host, manager_port))
    log("Redis: {}:{}".format(redis_host, redis_port))

    # resolve hostnames
    try:
        manager_host = socket.gethostbyname(manager_host)
        redis_host = socket.gethostbyname(redis_host)
    except Exception as e:
        log("Something went wrong while resolving hosts:")
        log(e)
        exit(1)

    # redis
    rds = RedisWrapper(redis_host, redis_port, REDIS_PW)

    # manager
    TaskManager.register('get_job_queue')
    m = TaskManager(address=(manager_host, manager_port), authkey = bytes(MANAGER_PW, encoding="ascii"))
    try:
        m.connect()
    except Exception as e:
        log("Exception while connecting to manager:")
        log(e)
        exit(1)
    log()
    log('connected to manager at {}:{}'.format(manager_host, manager_port))
    log()
    __start_worker(m)
