import numpy as np

from lib.helper import valueMap

class Planets:
    def __init__(self, num_planets):
        self.n      = num_planets
        self.pos    = np.empty((num_planets, 3), dtype=np.float64)
        self.speeds = np.empty((num_planets, 3), dtype=np.float64)
        self.accels = np.zeros((num_planets, 3), dtype=np.float64)
        self.masses = np.empty((num_planets, 1), dtype=np.float64)
        self.radii  = np.empty((num_planets, 1), dtype=np.float64)
        self.names  = ["unknown" for _ in range(num_planets)]

    def serialize(self):
        d = dict()
        d.update({
            "n": self.n,
            "pos": self.pos.tolist(),
            "speeds": self.speeds.tolist(),
            "accels": self.accels.tolist(),
            "masses": self.masses.tolist(),
            "radii": self.radii.tolist(),
            "names": self.names,
        })
        return d

    def deserialize(self, d: dict):
        #print("deserialize(), d:", d)
        self.n = d["n"]
        self.pos = np.array(d["pos"], dtype=np.float64)
        self.speeds = np.array(d["speeds"], dtype=np.float64)
        self.accels = np.array(d["accels"], dtype=np.float64)
        self.masses = np.array(d["masses"], dtype=np.float64)
        self.radii = np.array(d["radii"], dtype=np.float64)
        self.names = d["names"]
        return self

    #@jit
    def pos_to_renderable_numpy_array(self, scale_world, scale_planet=np.array((1))):
        """
        structure : [x,y,z,scale]
        :return: a numpy array representing the renderable part of this planet
        """

        # TODO use copy / reference here?

        l = []
        for i in range(self.n):

            pos_with_scale = np.empty((4), dtype=np.float64)
            pos_with_scale[0] = self.pos[i][0]
            pos_with_scale[1] = self.pos[i][1]
            pos_with_scale[2] = self.pos[i][2]

            # scale x (for opengl)
            pos_with_scale[0] = valueMap(pos_with_scale[0], -scale_world, scale_world, -1, 1)

            # scale y
            pos_with_scale[1] = valueMap(pos_with_scale[1], -scale_world, scale_world, -1, 1)

            # scale z
            pos_with_scale[2] = valueMap(pos_with_scale[2], -scale_world, scale_world, -1, 1)

            # add scale
            pos_with_scale[3] = self.radii[i] * scale_planet

            # append to planets list (only if planet isn't out of bounds)
            if (pos_with_scale[0] > -1.0 and pos_with_scale[0] < 1.0) and \
                (pos_with_scale[1] > -1.0 and pos_with_scale[1] < 1.0) and \
                (pos_with_scale[2] > -1.0 and pos_with_scale[2] < 1.0):
                l.append(pos_with_scale.tolist())

        return l

    def __deepcopy__(self, memodict={}):
        planets = Planets(self.n)
        planets.pos      = np.copy(self.pos)
        planets.speeds   = np.copy(self.speeds)
        planets.accels   = np.copy(self.accels)
        planets.masses   = np.copy(self.masses)
        planets.radii    = np.copy(self.radii)
        planets.names    = self.names[:]
        return planets

    def __copy__(self):
        return self.__deepcopy__()

    def __str__(self):
        return f"""Planets:
     Positions: {self.pos}
     Speeds: {self.speeds}
     Accelerations: {self.accels}
     masses: {self.masses}
     Radii: {self.radii}
     Names: {self.names}
                """