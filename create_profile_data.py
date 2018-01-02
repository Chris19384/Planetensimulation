from line_profiler import LineProfiler

from native import cyworker as worker
from lib.planet_helper import load_planets
from planets import Planets


def main():
    planets, _, _ = load_planets("planets.msgpack")
    new_planets = planets.__copy__()

    prof = LineProfiler()
    prof.add_function(worker.update_planet)
    prof.add_function(worker.move_planets)
    prof.runctx("toBench(planets, new_planets)", globals=globals(), locals=locals())
    prof.dump_stats("test.lprof")

def toBench(planets, new_planets):
    worker.move_planets(planets.pos,
                        planets.speeds,
                        planets.accels,
                        planets.masses,
                        new_planets.pos,
                        new_planets.speeds,
                        new_planets.accels,
                        new_planets.masses,
                        planets.n,
                        1500000
                        )


if __name__ == '__main__':
    main()