# nwws_oi_monitor

## Python Requirements
* Version +3.6
* Packages
* slixmpp
* libpython-static
* nuitka (if creating executable)

## Additional Requirements Under RedHat 8 to remove libpython linking issues
* sudo dnf install gcc-toolset-8-devel

## Enable GCC-Toolset-9
* scl enable gcc-toolset-9 bash

## Executable creation using Nuitka 
* python -m nuitka --standalone --include-package-data=slixmpp nww_oi_muc.py

## Move to /opt
sudo cp -R $HOME/nwwsoi-ldm/nww_oi_muc.dist /opt/nwwsoi-ldm
sudo chown -R ldm:ldm /opt/nwwsoi-ldm

## Command Line Execution 

`/opt/nwwsoi-ldm/nww_oi_muc --jid=<user id> --password=<password> --ldmcmd="<location of pqinsert>"`
