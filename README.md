# Planetensimulation

A semester project to learn about several technologies:

- (Py)Qt5
- Parallelization in Python
- Distribution using Python
- (Redis as a fast in-memory DB)



## Setup & Dependencies


### Debian (tested with Python 3.6.2)

apt-get's Python3 version is too old


``` bash
# compile & install python 3.6.2 | is this necessary?
cd /tmp
wget https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tar.xz
tar -xvf Python-3.6.3.tar.xz
cd Python-3.6.3/
./configure
make -j4
sudo make install
```

``` bash
sudo apt-get install python3-dev python3-pip
sudo pip3 install numpy numba cython
```


#### Archlinux

``` bash
# worker
pacman -Sy gcc python python-numpy cython python-pyqt5
```


### Windows (tested Windows 7?)

```
1. Download & install Python 3.6.x
    add '<python_install_dir>' and '<python_install_dir>\Scripts' to your System Path Variable
2. > pip3 install numpy cython pyqt5 pyopengl
3. Download & install 'Make for Windows' from here: http://gnuwin32.sourceforge.net/packages/make.htm
    add '<make_install_dir>\bin' to System Path
4. Download & install MinGW from here: http://www.mingw.org 
5.  from within MinGW Installation Manager, install
    - mingw32-base
    - mingw32-gcc
    - mingw-developer-toolkit
    - msys-base
6. GIVE UP! :D
```


## Build (native parts)

``` bash
make
```
    
    


## Run



### Simulation with GUI

``` bash
python3 simulation_gui.py
```




### Distributed System

Roles:

- Manager:
	- providing JobQueue and ResultQueue
    - default port: 33333

- Redis Server:
	- acting as key-value store for planet data
    - default port: 6379

- Worker(s):
    - connect to Manager & Redis
	- pull an item off the JobQueue
	- pull planet data from redis
	- calculate result data
	- store result in redis



#### Worker Setup

- ArchlinuxARM (tested with Raspberry Pi)

    ``` bash
    # install dependencies
    sudo pacman -Sy git make gcc python python-numpy cython

    # compile cython code
    make
    ```

    Default ports:

    - manager: 33333
    - redis: 6379


- Archlinux:

    See [Dockerfile](cl/docker/Dockerfile.archlinux)

    and

    [Makefile](cl/docker/Makefile)



##### Run distributed system

TODO document starting redis

- Manager

    ``` bash
    # launch on default port 33333
    make clmanager
    ```

- Workers

    ``` bash
    make clworker HOST=<hostname_of_manager>
    
    # or (for non-localhost cluster)
    python3 distributed_worker.py <m_host> <m_port> <r_host> <r_port>
    ```

