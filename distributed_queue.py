from multiprocessing.managers import SyncManager, BaseManager
from multiprocessing import JoinableQueue, Queue

from planets import Planets


SECRET = 'secret'
MAX_ITEMS = 999999999


class TaskManager(SyncManager):
    pass

if __name__ == '__main__':
    from sys import argv, exit
    if len(argv) != 2:
        print('usage:', argv[0], b'socket_nr')
        exit(0)
    master_socket = int(argv[1])
    task_queue = JoinableQueue()
    result_queue = Queue()

    # dummy
    shared_dict = {}

    TaskManager.register('get_job_queue',
                         callable = lambda:task_queue)
    TaskManager.register('get_result_queue',
                         callable = lambda:result_queue)
    TaskManager.register('get_shared_dict',
                         callable = lambda: shared_dict)
    m = TaskManager(address = ('', master_socket),
                    authkey = bytes(SECRET, encoding='ascii'))

    # info
    print('starting queue server, socket', master_socket)
    #print(f"task_queue capacity:   {task_queue}")
    #print(f"result_queue capacity: {result_queue}")


    # GO!
    m.get_server().serve_forever()

    # data dict
    shared_dict = m.dict()
    #shared_dict.update({
    #    'pos': None,
    #    'speeds': None,
    #    'accels': None,
    #    'masses': None,
    #    'n': None
    #})

    # publish dict
    #m.register('get_shared_dict', callable=lambda: shared_dict)
