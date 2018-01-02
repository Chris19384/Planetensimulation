# Planetensimulation

A semester project to learn about several technologies:

- PyQt5
- Parallelization in Python
- Distribution using Python
- (Redis as a fast in-memory DB)



## Dependencies


install miniconda and you'll mostly be fine


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
