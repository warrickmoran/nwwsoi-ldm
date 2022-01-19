# nwwsoi-ldm

## Python Requirements
* Version +3.6
* Packages
* slixmpp
* libpython-static
* psutil
* nuitka (if creating executable)

## Additional Requirements Under RedHat 8 to remove libpython linking issues
* sudo dnf install gcc-toolset-9-binutils-devel

## Enable GCC-Toolset-9
* scl enable gcc-toolset-9 bash

## Executable creation using Nuitka 
* sudo python -m nuitka --standalone --include-package-data=slixmpp --remove-output nww_oi_muc.py

## Move to /opt
* sudo cp -R <repository>/nwwsoi-ldm/nww_oi_muc.dist /opt/nwwsoi-ldm
* sudo chown -R ldm:ldm /opt/nwwsoi-ldm

## Command Line Execution 

`/opt/nwwsoi-ldm/nww_oi_muc --jid=<user id> --password=<password> --ldm`
