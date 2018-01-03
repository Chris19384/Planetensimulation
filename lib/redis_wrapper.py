import numpy as np

from . import redis
from .planet_helper import serialize_np, deserialize_np
from .helper import get_log_func


log = get_log_func("[RedisWrapper]")


class RedisWrapper():
    """
    A Redis Wrapper containing specific
    methods to use within planet simulation
    """

    def __init__(self, host='localhost', port=6379, password=''):
        try:
            # redis connection instance
            self.r = redis.StrictRedis(host=host, port=port, password=password, db=0)
            print()
            log()
            log(f"<> connected to {host}:{port}")
            log()
        except Exception as e:
            raise ConnectionError(e)

    def send_planets(self, pos: np.ndarray,
                       speeds: np.ndarray,
                       accels: np.ndarray,
                       masses: np.ndarray,
                       n):
        self.r.set('pos', (serialize_np(pos)))
        self.r.set('speeds', (serialize_np(speeds)))
        self.r.set('accels', (serialize_np(accels)))
        self.r.set('masses', (serialize_np(masses)))
        self.r.set('n', n)

    def send_planets_wo_masses(self, pos: np.ndarray,
                       speeds: np.ndarray,
                       accels: np.ndarray,
                       n):
        self.r.set('pos', (serialize_np(pos)))
        self.r.set('speeds', (serialize_np(speeds)))
        self.r.set('accels', (serialize_np(accels)))
        self.r.set('n', n)


    def receive_planets(self):
        pos = deserialize_np((self.r.get('pos')))
        speeds = deserialize_np((self.r.get('speeds')))
        accels = deserialize_np((self.r.get('accels')))
        masses = deserialize_np((self.r.get('masses')))
        n = int(self.r.get('n'))
        return pos, speeds, accels, masses, n

    def get_np(self, key):
        return deserialize_np((self.r.get(key)))

    def set_np(self, key, val):
        return self.r.set(key, (serialize_np(val)))

    def delete(self, key):
        self.r.delete(key)
