from lib.redis_wrapper import RedisWrapper
from lib.helper import get_log_func, time_ms, chunk_indices

from distributed_queue import TaskManager

log = get_log_func("[DistMaster]")


class DistributedMaster:
    """
    Class to connect to a cluster and redis instance
    and execute tasks
    """

    def __init__(self, config):

        self.rds = None
        self.rds_connected = False

        self.tm = None
        self.job_queue = None
        self.tm_connected = False

        self.masses_pushed = False
        self.ok = False
        self.config = config
        self.chunks = config.cluster["chunks"]
        self.run_id = 0

        # debug vars
        self.dg_cluster_result = config.debug["cluster_result"]
        self.dg_cluster_times = config.debug["cluster_times"]

        # setup redis
        try:
            self.rds = RedisWrapper(config.cluster["redis_host"], config.cluster["redis_port"],
                               config.cluster["redis_secret"])
            self.rds_connected = True
        except Exception as e:
            log("Exception while connecting to Redis:", e)
            self.rds_connected = False

        # setup connection to manager
        m_host = config.cluster["manager_host"]
        m_port = config.cluster["manager_port"]
        TaskManager.register('get_job_queue')
        tm = TaskManager(address=(m_host, m_port),
                         authkey=bytes(config.cluster["manager_secret"], encoding='ascii'))
        try:
            tm.connect()
            self.job_queue = tm.get_job_queue()
            self.tm_connected = True
        except Exception as e:
            log("Exception while connecting to Manager:", e)
            self.tm_connected = False

        self.ok = self.rds_connected and self.rds_connected




    def calculate_planets(self, planets, new_planets, delta_t):
        # first, clear out queue
        while not self.job_queue.empty():
            log()
            log(" OLD ITEM FOUND in self.job_queue. deleting!")
            log()
            self.job_queue.get_nowait()

        # calculate job indices for the given chunksize
        t_start_chunk_indices = time_ms()
        index_tuples = list(chunk_indices(planets.n, self.chunks))
        t_chunk_indices = time_ms() - t_start_chunk_indices

        # push planet data to redis
        t_start_dict_update = time_ms()
        if not self.masses_pushed:
            self.rds.send_planets(planets.pos, planets.speeds, planets.accels, planets.masses, planets.n)
            self.masses_pushed = True
        else:
            self.rds.send_planets_wo_masses(planets.pos, planets.speeds, planets.accels, planets.n)
        t_dict_update = time_ms() - t_start_dict_update

        # distribute jobs to the waiting worker(s)
        t_start_put = time_ms()
        for tpl in index_tuples:
            self.job_queue.put((tpl[0], tpl[1], delta_t, self.run_id))
        t_put = time_ms() - t_start_put

        # block as long as result is not computed by all workers
        t_join_start = time_ms()
        self.job_queue.join()
        t_join = time_ms() - t_join_start

        if self.dg_cluster_result:
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
            r_pos, r_speeds, r_accels = self.rds.get_np(key_pos), self.rds.get_np(key_speeds), self.rds.get_np(key_accels)

            # del redis
            self.rds.delete(key_pos)
            self.rds.delete(key_speeds)
            self.rds.delete(key_accels)

            # timing
            t_queue += time_ms() - t_queue_get

            # merge values in our data
            t_start_merge = time_ms()
            new_planets.pos[ifrom:ito][:] = r_pos[:][:]
            new_planets.speeds[ifrom:ito][:] = r_speeds[:][:]
            new_planets.accels[ifrom:ito][:] = r_accels[:][:]
            t_merge_all += time_ms() - t_start_merge

        t_redis_apply = time_ms() - t_start_redis_apply

        if self.dg_cluster_result:
            log(f"cluster apply sum {sqsum}")

        # measure performance
        if self.dg_cluster_times:
            log()
            log(f"    chunkup      : {t_chunk_indices}ms")
            log(f"    u_dict       : {t_dict_update}ms")
            log(f"    q_put        : {t_put}ms")
            log(f"    join         : {t_join}ms")
            log(f"    t_merge      : {t_merge_all}ms")
            log(f"    redis_apply  : {t_redis_apply}ms")
            log(f"      q_get      : {t_queue}ms")
            log()

        self.run_id += 1

    def is_healthy(self):
        return self.ok

    def cleanup(self, planets):
        # spray and hope every worker gets at least one job
        # TODO this is bad.........
        jobs = 4 * len(list(chunk_indices(planets.n, self.chunks)))
        for i in range(jobs):
            self.job_queue.put((-1337, 0, 0, 0))