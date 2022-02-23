# nwwsoi-ldm

## Prerequisite
* LDMD
* Python +3.8

## Python Requirements
* Version +3.8
* Packages
* slixmpp
* libpython-static
* psutil
* nuitka (if creating executable)

## Conda VirtEnv Setup (optional)
* conda create --name nwws python=3.8 slixmpp libpython-static nuitka pyyaml coloredlogs psutil patchelf

## Additional Requirements Under RedHat 8 to remove libpython linking issues
* sudo dnf install gcc-toolset-9-binutils-devel

## Enable GCC-Toolset-9
* scl enable gcc-toolset-9 bash

## Activate VirtEnv "nwws"
* (if using conda) conda activate nwws

## Executable creation using Nuitka 
* python -m nuitka --standalone --include-package-data=slixmpp --remove-output nwwsoi-ldm.py

## Move to /opt
* sudo cp -R \<repository\>/nwwsoi-ldm/nwwsoi-ldm.dist /opt/nwwsoi_ldm
* sudo chown -R ldm:ldm /opt/nwwsoi_ldm

## Command Line Execution 
`/opt/nwwsoi_ldm/nwwsoi-ldm --jid=<user id> --password=<password> --ldm`
