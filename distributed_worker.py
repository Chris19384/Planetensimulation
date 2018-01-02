from distributed_queue import TaskManager
from sys import argv, exit

from native.cyworker import update_planet_indices
from lib.redis_wrapper import RedisWrapper
from lib.helper import time_ms, get_log_func


REDIS_PW = "NotEvenSecureRedis"


# RedisWrapper instance
rds: RedisWrapper = None
log = get_log_func("[worker]")




def __worker_function(job_queue, result_queue):

    # work forever
    while 1:

        # pull a task from the queue (blocking call)
        t_start_get = time_ms()
        task = job_queue.get()
        ifrom, ito, delta_t = task
        t_get = time_ms() - t_start_get


        # get planet data from redis server
        t_start_dict = time_ms()
        pos, speeds, accels, masses, n = rds.receive_planets()
        t_dict = time_ms() - t_start_dict


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
        result_queue.put(1)


        # send back a signal that this job is done
        job_queue.task_done()
        t_calc = time_ms() - t_start_calc


        # timing information
        log(f"Job from {ifrom:5d} to {ito:5d}")
        log(f"  t_get : {t_get}ms")
        log(f"  t_dict: {t_dict}ms")
        log(f"  t_calc: {t_calc}ms")
        log()

def __start_worker(m):
    job_queue, result_queue = m.get_job_queue(), m.get_result_queue()
    __worker_function(job_queue, result_queue)

if __name__ == '__main__':

    # parse commandline arguments
    if len(argv) < 5:
        log('usage:', argv[0], '<manager_host> <manager_port> <redis_host> <redis_port>')
        exit(0)
    manager_host = argv[1]
    manager_port = int(argv[2])
    redis_host   = argv[3]
    redis_port   = int(argv[4])

    # redis
    rds = RedisWrapper(redis_host, redis_port, REDIS_PW)

    # manager
    TaskManager.register('get_job_queue')
    TaskManager.register('get_result_queue')
    m = TaskManager(address=(manager_host, manager_port), authkey = b'secret')
    while 1:
        try:
            m.connect()
            break
        except:
            log("reconnecting...")
    log()
    log(f"connected to manager at {manager_host}:{manager_port}")
    log()
    __start_worker(m)