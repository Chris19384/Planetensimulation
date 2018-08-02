# build by katze
with import <nixpkgs> {};
stdenv.mkDerivation rec {
	name = "env";
	env = buildEnv { name = name; paths = buildInputs; };
	buildInputs = [
		python36Packages.numpy
		python36Packages.numba
		python36Packages.cython
		python36Packages.pyqt5
		python36Packages.pyopengl
		gnumake
		python36Full
	];
}

