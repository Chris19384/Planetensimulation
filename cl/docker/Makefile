all:

archbuild:
	# TODO: build native and redis before building docker image
	docker build ../../../ -f Dockerfile.archlinux -t worker	

archrun:
	docker run --name="SimWorker" -it --net="host" worker bash 
