"""
This module should contain methods for interacting with a config file
"""

import json
import numpy as np

from lib.helper import get_log_func



log = get_log_func("[config]")
DEBUG = False


class Config:
    """
    Wrapper for a config file.
    Loads values from default config file.
    Access via point operator:
    >>> c: Config = Config("save.cfg.json")
    >>> c.delta_t_max
    50000000.0

    Values can also be set using the same operator
    >>> c.delta_t_max = 200.0

    Save the config to the file with the filename provided in the constructor
    >>> #c.save()
    """

    def __init__(self, filename, filename_default='default.cfg.json'):
        """
        Initialize Config with constants defined in
        simulation_constants.py
        """

        self.filename = filename_default
        self.load()
        self.filename = filename


    def load(self):
        """
        Load up this class's config parameters
        by parsing the contents of the file self.filename
        :return:
        """
        try:
            with open(self.filename, 'r') as file:

                # read raw
                content_raw = file.read()
                if DEBUG:
                    log("\nDump raw:")
                    log(content_raw)

                # parse
                content = json.loads(content_raw)
                if DEBUG:
                    log("\nDump parsed:")
                    log(content)

                # load stuff
                self.keys = []
                for k, v in content.items():
                    self.keys.append(k)
                    self.__dict__[k.lower()] = v

        except FileNotFoundError as e:
            log(f"ERROR: file {self.filename} not found")
            log(f"load() failed. {e}")

    def save(self):
        try:
            with open(self.filename, 'w') as file:

                # get all writable attributes
                d = dict()
                for k in self.keys:
                    v = self.__dict__[k]
                    if isinstance(v, np.ndarray):
                        d.update({k: v.tolist()})
                    else:
                        d.update({k: v})

                # write out
                raw = json.dumps(d, indent=4)
                file.write(raw)
            if DEBUG:
                log(f"Saved to file {self.filename}")
        except Exception as e:
            log(f"ERROR: Save to file {self.filename} failed.")
            log(f"{e}")


def main():
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    main()
