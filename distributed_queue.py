from multiprocessing.managers import SyncManager
from multiprocessing import JoinableQueue, Queue
from sys import argv, exit

from config import Config


config = Config("save.cfg.json")
SECRET = config.cluster["manager_secret"]


class TaskManager(SyncManager):
    pass


def main():
    if len(argv) != 2:
        print('usage:', argv[0], b'socket_nr')
        exit(0)
    master_socket = int(argv[1])
    task_queue = JoinableQueue()
    result_queue = Queue()

    TaskManager.register('get_job_queue',
                         callable=lambda: task_queue)
    TaskManager.register('get_result_queue',
                         callable=lambda: result_queue)
    m = TaskManager(address=('', master_socket),
                    authkey=bytes(SECRET, encoding='ascii'))

    # info
    print('starting queue server, socket', master_socket)

    # GO!
    m.get_server().serve_forever()


if __name__ == '__main__':
    main()
