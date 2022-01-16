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
* python -m nuitka --standalone --static-libpython=yes nww_oi_muc.py

## Command Line Execution 

`./dist/nww_oi_muc --jid=<user id> --password=<password>`

## Command Line Execution with Visualization

`./dist/nww_oi_muc --jid=<user id> --password=<password> --metrics`
