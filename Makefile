SRCS=$(shell echo ./*.py)
MHOST=127.0.0.1
MPORT=33333
RHOST=127.0.0.1
RPORT=6379
REDISCONFIG=./lib/redis.conf

all: buildnative

buildnative:
	cd native; make; cd -

lint:
	@echo
	@echo ---
	@echo - linting
	@echo ---
	pylint $(SRCS)

test:
	@echo
	@echo ---
	@echo - testing
	@echo ---
	@echo NO TESTS set up in Makefile...
#	for src in $(SRCS) ; do \
		/usr/bin/python3.6 $$src ; \
	done

profile:
	pyprof2calltree -k -i /tmp/galaxy_profile.cprof

run:
	python3.6 simulation_gui.py

clean:
	rm planets.msgpack save.cfg.json


fixredis:
	echo never > /sys/kernel/mm/transparent_hugepage/enabled

redis:
	./lib/redis-server/src/redis-server $(REDISCONFIG) --protected-mode no

clmanager:
	python3.6 distributed_queue.py 33333 &

clworker:
	python3.6 distributed_worker.py $(MHOST) $(MPORT) $(RHOST) $(RPORT) &

cl: clmanager clworker

clkill:
	ps aux | grep 'python3.6 distributed' | awk '{print $$2}' | xargs kill


nix: 
	nix-shell
