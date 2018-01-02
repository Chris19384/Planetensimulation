# Planetensimulation

A semester project to learn about several technologies:

- (Py)Qt5
- Parallelization in Python
- Distribution using Python
- (Redis as a fast in-memory DB)



## Dependencies


install [miniconda3](https://conda.io/miniconda.html) and you'll mostly be fine


#### Debian

Tested with Python 3.6.2

apt-get's Python3 version is too old


``` bash
# compile & install python 3.6.2 | is this necessary?
cd /tmp
wget https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tar.xz
tar -xvf Python-3.6.3.tar.xz
cd Python-3.6.3/
./configure
make
sudo make install
```

``` bash
sudo apt-get install python3-dev python3-pip
sudo pip3 install numpy numba cython
```

#### Archlinux

``` bash
# TODO not complete...
pacman -Sy python
```

- miniconda ( PyQt5, ...)



## Build (native parts)


``` bash
make
```
    
    


## Run



### Simulation with GUI

``` bash
python3 simulation_gui.py

# or

make run
```




#### Distributed System

Roles:

- Manager:
	- providing JobQueue and ResultQueue

- Redis Server:
	- acting as key-value store for planet data

- Worker(s):
	- pull an item off the JobQueue
	- pull planet data from redis
	- calculate result data
	- store result in redis


Default ports:

- manager: 33333
- redis: 6379


##### Manager

``` bash
# launch on default port 33333
make clmanager
```

##### workers

``` bash
make clworker HOST=<hostname_of_manager>
```




### Licence

MIT
