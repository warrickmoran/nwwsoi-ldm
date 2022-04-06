'''
Created on Dec 3, 2019

@author: warrick.moran
'''
from slixmpp.xmlstream.stanzabase import ElementBase

class X(ElementBase):
    namespace = 'nwws-oi'
    name = 'x'
    plugin_attrib = 'x'
    interfaces = set(('cccc', 'ttaaii', 'issue', 'awipsid', 'id'))
    sub_interfaces = interfaces

        