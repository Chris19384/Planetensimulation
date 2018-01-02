""" simple PyQt5 simulation controller
#
# Copyright (C) 2017  "Peter Roesch" <Peter.Roesch@fh-augsburg.de>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# or open http://www.fsf.org/licensing/licenses/gpl.html
#
"""


import multiprocessing
import sys
import numpy as np
import lib.umsgpack as umsgpack

from PyQt5 import QtWidgets, uic

import galaxy_renderer
import simulation as simulation
from config import Config
from lib.helper import get_log_func
from simulation_constants import END_MESSAGE

CONFIG_FILE = "save.cfg.json"
PLANETS_FILE = "planets.msgpack"
SHOULD_LOAD_LAST_CONFIG_ON_STARTUP = True
DEBUG_GUI = False


__log = get_log_func("[gui]")

def log(*tpl):
    if DEBUG_GUI:
        __log(*tpl)


class SimulationGUI(QtWidgets.QWidget):
    """
        Widget with two buttons
    """
    def __init__(self):
        QtWidgets.QWidget.__init__(self)

        self.ui = uic.loadUi('userinterface.ui')
        self.config = Config(CONFIG_FILE) # pylint:disable=no-member

        # modes combobox
        for i, mode in enumerate(self.config.mode_stuff["modes"]):
            self.ui.comboBoxMode.insertItem(i, mode)
        self.ui.comboBoxMode.currentIndexChanged.connect(self.change_mode)

        # update impl combobox
        for i, impl in enumerate(self.config.update_impls):
            self.ui.comboBoxUpdateImpl.insertItem(i, impl)
        self.ui.comboBoxUpdateImpl.currentTextChanged.connect(self.change_update_impl)


        self.ui.start_button.clicked.connect(self.start_simulation)
        self.ui.pause_button.clicked.connect(self.pause_simulation)
        self.ui.stop_button.clicked.connect(self.stop_simulation)
        self.ui.quit_button.clicked.connect(self.exit_application)

        self.ui.sliderRenderFps.valueChanged.connect(self.change_render_fps)
        self.ui.sliderSimFps.valueChanged.connect(self.change_sim_fps)

        self.ui.delta_slider.valueChanged.connect(self.change_delta)

        self.ui.checkBoxProfile.stateChanged.connect(self.change_profile)

        # # planets
        self.ui.slider_num_planets.valueChanged.connect(self.change_num_planets)

        # config
        self.ui.load_config_button.clicked.connect(self.load_config)
        self.ui.save_config_button.clicked.connect(self.save_config)
        self.ui.load_config_defaults_button.clicked.connect(self.load_defaults_config)

        # load/save planets btns
        self.ui.button_save_planets.clicked.connect(self.save_planets)
        self.ui.edit_planetfile.textChanged.connect(self.change_planets_file)

        # completers
        comp_host = QtWidgets.QCompleter(self.config.cluster["suggested_hosts"], self)
        comp_host.setCaseSensitivity(0)
        comp_port = QtWidgets.QCompleter(self.config.cluster["suggested_ports"], self)
        comp_port.setCaseSensitivity(0)


        # cluster settings
        self.ui.checkBox_cluster.stateChanged.connect(self.change_cluster_active)
        self.ui.spinBox_chunks.valueChanged.connect(self.change_cluster_chunks)

        self.ui.lineEdit_cluster_m_host.textChanged.connect(self.change_cluster_m_host)
        self.ui.lineEdit_cluster_m_host.setCompleter(comp_host)
        self.ui.lineEdit_cluster_m_port.textChanged.connect(self.change_cluster_m_port)
        self.ui.lineEdit_cluster_m_port.setCompleter(comp_port)

        self.ui.lineEdit_cluster_r_host.textChanged.connect(self.change_cluster_r_host)
        self.ui.lineEdit_cluster_r_host.setCompleter(comp_host)
        self.ui.lineEdit_cluster_r_port.textChanged.connect(self.change_cluster_r_port)
        self.ui.lineEdit_cluster_r_port.setCompleter(comp_port)


        self.d = self.ui.label_delta_d
        self.h = self.ui.label_delta_h
        self.m = self.ui.label_delta_m
        self.s = self.ui.label_delta_s

        self.renderer_conn, self.simulation_conn = None, None
        self.render_process = None
        self.simulation_process = None
        multiprocessing.set_start_method('spawn')

        if SHOULD_LOAD_LAST_CONFIG_ON_STARTUP:
            self.config.load()

        # load default values into GUI
        self.reload_from_config()

        # flag showing if simulation is paused
        self.paused = False

        # flag indicating if we should load old planet data
        self.load_planet_data = False

        # show ui
        self.ui.show()


    def reload_from_config(self):
        """ Load all Config params into the GUI """

        self.ui.spinBoxDelta.setMinimum(self.config.delta_t_min)
        self.ui.spinBoxDelta.setMaximum(self.config.delta_t_max)
        self.ui.delta_slider.setMinimum(self.config.delta_t_min)
        self.ui.delta_slider.setMaximum(self.config.delta_t_max)
        self.ui.spinBoxDelta.setValue(self.config.delta_t)
        self.change_delta(self.config.delta_t)

        self.ui.sliderRenderFps.setMinimum(self.config.fps_min)
        self.ui.sliderRenderFps.setMaximum(self.config.fps_max)
        self.ui.sliderSimFps.setMinimum(self.config.fps_min)
        self.ui.sliderSimFps.setMaximum(self.config.fps_max)
        self.ui.sliderRenderFps.setValue(self.config.render_fps)
        self.ui.sliderSimFps.setValue(self.config.sim_fps)

        # planets
        self.ui.slider_num_planets.setValue(self.config.nr_planets)

        # profile
        self.ui.checkBoxProfile.setCheckState(bool(self.config.profile))

        # mode box
        self.ui.comboBoxMode.setCurrentIndex(self.config.mode_stuff["mode"])

        # update
        self.ui.comboBoxUpdateImpl.setCurrentIndex(self.config.update_impls.index(self.config.update_impl))

        # cluster settings
        self.ui.checkBox_cluster.setCheckState(2 if self.config.cluster["active"] else 0)
        self.ui.spinBox_chunks.setMinimum(self.config.cluster["chunks_min"])
        self.ui.spinBox_chunks.setMaximum(self.config.cluster["chunks_max"])
        self.ui.dial_chunks.setMinimum(self.config.cluster["chunks_min"])
        self.ui.dial_chunks.setMaximum(self.config.cluster["chunks_max"])
        self.ui.spinBox_chunks.setValue(self.config.cluster["chunks"])
        self.ui.lineEdit_cluster_m_host.setText(self.config.cluster["manager_host"])
        self.ui.lineEdit_cluster_m_port.setText(str(self.config.cluster["manager_port"]))
        self.ui.lineEdit_cluster_r_host.setText(self.config.cluster["redis_host"])
        self.ui.lineEdit_cluster_r_port.setText(str(self.config.cluster["redis_port"]))


        # load planets stuff
        self.ui.edit_planetfile.setText(self.config.load_planets_file)
        if self.config.mode_stuff["mode"] == "last planet data":
            self.ui.edit_planetfile.setEnabled(True)
        else:
            self.ui.edit_planetfile.setEnabled(False)




    def start_simulation(self):
        """
            Start simulation and render process connected with a pipe.
        """

        # create a pipe which solely purpose is to send commands to the simulation
        self.renderer_conn, self.simulation_conn = multiprocessing.Pipe()
        if self.config.profile:
            self.simulation_process = \
                multiprocessing.Process(target=simulation.startup_profile,
                                        args=(self.simulation_conn, self.config))
        else:
            self.simulation_process = \
                multiprocessing.Process(target=simulation.startup,
                                        args=(self.simulation_conn, self.config))

        self.render_process = \
            multiprocessing.Process(target=galaxy_renderer.startup,
                                    args=(self.renderer_conn, self.config.render_fps), )
        self.simulation_process.start()
        self.render_process.start()
        self.paused = True
        self.pause_simulation()


    def pause_simulation(self):
        if self.paused:
            if self.renderer_conn is not None:
                self.renderer_conn.send({"paused": False})
                self.ui.pause_button.setText("Pause")
                self.paused = False

        else:
            if self.renderer_conn is not None:
                self.renderer_conn.send({"paused": True})
                self.ui.pause_button.setText("Resume")
                self.paused = True


    def stop_simulation(self):
        """
            Stop simulation and render process by sending END_MESSAGE
            through the pipes.
        """
        if self.simulation_process is not None:
            self.simulation_conn.send_bytes(umsgpack.packb(END_MESSAGE))
            self.simulation_process = None

        if self.render_process is not None:
            self.renderer_conn.send(END_MESSAGE)
            self.render_process = None

    def exit_application(self):
        """
            Stop simulation and exit.
        """
        self.stop_simulation()
        self.ui.close()

    def change_render_fps(self, new_fps):
        log("change_render_fps not implemented")
        self.config.render_fps = new_fps

    def change_sim_fps(self, new_fps):
        if self.renderer_conn is not None:
            log("change_fps in GUI:", new_fps)
            self.renderer_conn.send({"fps": new_fps})
        self.config.sim_fps = new_fps

    def change_delta(self, new_delta):

        # set value
        if self.renderer_conn is not None:
            log("change_delta in GUI:", new_delta)
            self.renderer_conn.send({"delta_t": new_delta})

        # as numpy array (to speed up calculations)
        new_delta_np = np.array((new_delta), dtype=np.int32)

        # update widgets
        days = new_delta_np / (60 * 60 * 24)
        rest = days - np.floor(days)
        days = np.floor(days)

        hours = rest * 24
        rest = hours - np.floor(hours)
        hours = np.floor(hours)

        minutes = rest * 60
        rest = minutes - np.floor(minutes)
        minutes = np.floor(minutes)

        seconds = np.floor(rest * 60)

        self.d.setText(str(days.tolist()))
        self.h.setText(str(hours.tolist()))
        self.m.setText(str(minutes.tolist()))
        self.s.setText(str(seconds.tolist()))

        self.config.delta_t = new_delta

    def change_mode(self, newMode: int):
        self.config.mode_stuff["mode"] = newMode
        if newMode == "last planet data":
            self.ui.edit_planetfile.setEnabled(True)
        else:
            self.ui.edit_planetfile.setEnabled(False)
        log(f"change mode to {newMode}")

    def change_update_impl(self, newImpl):
        self.config.update_impl = newImpl
        log(f"change update impl to {newImpl}")

    def change_profile(self, should):
        self.config.profile = bool(should)
        log(f"change profile to {bool(should)}")

    def change_planets_file(self, str):
        self.config.load_planets_file = str
        log(f"change_planets_file: {str}")

    def change_num_planets(self, nr):
        self.config.nr_planets = nr
        log(f"change_num_planets: {nr}")

    def change_cluster_active(self, state):
        self.config.cluster["active"] = True if state == 2 else False
        log(f"change_cluster_active: {True if state == 2 else False}")

    def change_cluster_chunks(self, new_chunks):
        self.config.cluster["chunks"] = new_chunks
        if self.renderer_conn is not None:

            self.renderer_conn.send({"chunks": new_chunks})
        log(f"change_cluster_chunks: {new_chunks}")

    def change_cluster_m_host(self, new_host):
        self.config.cluster["manager_host"] = new_host
        log(f"change_cluster_m_host: {new_host}")
        pass

    def change_cluster_m_port(self, new_port):
        p = int(new_port if new_port != '' else 0)
        self.config.cluster["manager_port"] = p
        log(f"change_cluster_m_port: {p}")
        pass

    def change_cluster_r_host(self, new_host):
        self.config.cluster["redis_host"] = new_host
        log(f"change_cluster_r_host: {new_host}")
        pass

    def change_cluster_r_port(self, new_port):
        p = int(new_port if new_port != '' else 0)
        self.config.cluster["redis_port"] = p
        log(f"change_cluster_r_port: {p}")
        pass

    def save_planets(self):
        if self.renderer_conn is not None:
            log("save_planets in GUI")
            self.renderer_conn.send({"save_planets": self.config.load_planets_file})


    def load_config(self):
        self.config.load()
        self.reload_from_config()
        log(f"load_config(), config loaded from file")

    def save_config(self):
        self.config.save()
        log(f"save_config()")

    def load_defaults_config(self):
        self.config = Config(CONFIG_FILE)
        self.reload_from_config()
        log(f"load_defaults_config()")

    def set_profile_file(self, file):
        self.config.profile_file = file



def _main(argv):
    """
        Main function to avoid pylint complains concerning constant names.
    """
    app = QtWidgets.QApplication(argv)
    simulation_gui = SimulationGUI()
    #simulation_gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    _main(sys.argv)