"""
 This ingest process will see just about every text product that comes down
 the LDM pipe.  It will base its routing on the products found within the
 database.

"""
#from syslog import LOG_LOCAL2
#from twisted.python import syslog
#syslog.startLogging(prefix='pyWWA/nwws_processor',  facility=LOG_LOCAL2)
#from twisted.python import log
from twisted.python import log
from twisted.python import logfile

# rotate every 100 bytes
f = logfile.LogFile("test.log", "/tmp", rotateLength=10000)
# setup logging to use our new logfile
log.startLogging(f)

from twisted.internet import reactor
from twisted.words.xish import domish, xpath
from twisted.internet.task import LoopingCall
from twisted.words.xish.xmlstream import STREAM_END_EVENT
from twisted.words.protocols.jabber import xmlstream, jid
from twisted.words.protocols.jabber import client as jclient

from pyiem.nws.product import TextProduct
from pyiem import reference 
from pyldm import ldmbridge 

import os
import datetime
import re
import traceback
import common # Not part of Python3 library (outdated)
_illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')

common.write_pid("nwws_processor")

# LDM Ingestor
class MyProductIngestor(ldmbridge.LDMProductReceiver):
    """ I receive products from ldmbridge and process them 1 by 1 :) """

    def __init__(self, dedup):
        """ Constructor """
        self.sequence = 0
        self.process = os.getpid()
        ldmbridge.LDMProductReceiver.__init__(self, dedup)

    def connectionLost(self, reason):
        log.msg('connectionLost')
        log.err( reason )
        reactor.callLater(7, self.shutdown)

    def shutdown(self):
        reactor.callWhenRunning(reactor.stop)

    def process_data(self, buf):
        """ Process the product """
        try:
            self.really_process( buf )
        except Exception as myexp:
            print (buf[:40])
            print (traceback.format_exc())
            log.err(myexp)
            pass #TODO
            #common.email_error(myexp, buf)

    def really_process(self, raw ):
        """ Do something with this raw text our ldmbridge provided us """
        tp = TextProduct( raw )
        # perhaps this is not 'threadsafe'
        self.sequence += 1
        xtra = {'id': '%s.%s' % (self.process, self.sequence)}
        xtra['payload'] = _illegal_xml_chars_RE.sub('', raw)
        xtra['issue'] = tp.valid.strftime("%Y-%m-%dT%H:%M:%SZ")
        xtra['ttaaii'] = tp.wmo
        xtra['cccc'] = tp.source
        if tp.afos is None:
            tp.afos = ''
        xtra['awipsid'] = tp.afos
        msg = "%s issues %s valid %s" % (tp.source, 
                                     reference.prodDefinitions.get(tp.afos[:3], 
                                                                   tp.afos[:3]), 
                                     tp.valid.strftime("%Y-%m-%dT%H:%M:%SZ"))
        jabber.sendMessage(msg, None, xtra)
        log.msg("product |%s| sent to chatroom" % (tp.get_product_id(),))

class JabberClient:
    """
    I am an important class of a jabber client against the chat server,
    used by pretty much every ingestor as that is how messages are routed
    to nwsbot
    """

    def __init__(self, myJid):
        """
        Constructor 
        
        @param myJid twisted.words.jid object
        """
        self.myJid = myJid
        self.xmlstream = None
        self.authenticated = False
        self.myroom = None

    def presence_processor(self, elem):
        """ Process presence stanzas """
        #log.msg( elem.toXml() )
        items = xpath.queryForNodes("/presence/x[@xmlns='http://jabber.org/protocol/muc#user']/item", elem)
        if items is None:
            return
        room = jid.JID( elem["from"] ).user
        #handle = jid.JID( elem["from"] ).resource
        for item in items:
            affiliation = item.getAttribute('affiliation')
            _jid = item.getAttribute('jid')
            role = item.getAttribute('role')
            log.msg("room: %s _jid: %s role: %s affiliation: %s" % (room,
                                                                    _jid,
                                                                    role,
                                                                    affiliation))
            if not self.roominfo.has_key(room):
                log.msg("Initialize roominfo for: %s" % (room,))
                self.roominfo[room] = {'count': 0}
            if role == 'none':
                self.roominfo[room]['count'] -= 1
            else:
                self.roominfo[room]['count'] += 1


    def message_processor(self, stanza):
        """ Process a message stanza """
        body = xpath.queryForString("/message/body", stanza)
        #log.msg("Message from %s Body: %s" % (stanza['from'], body))
        if body is None:
            return
        if body.lower().strip() == "shutdown":
            log.msg("I got shutdown message, shutting down...")
            shutdown()

    def authd(self,xs):
        """
        Callbacked once authentication succeeds
        @param xs twisted.words.xish.xmlstream
        """
        log.msg("Logged in as %s" % (self.myJid,))
        self.authenticated = True
        self.roominfo = {}
        self.xmlstream = xs

        
        #self.xmlstream.rawDataInFn = self.rawDataInFn
        #self.xmlstream.rawDataOutFn = self.rawDataOutFn
        
        # Process Messages
        self.xmlstream.addObserver('/message/body',  self.message_processor)
        self.xmlstream.addObserver('/presence/x/item',  self.presence_processor)
        
        # Send initial presence
        presence = domish.Element(('jabber:client','presence'))
        presence.addElement('status').addContent('Online')
        self.xmlstream.send(presence)
        
        # Join our chatroom
        presence = domish.Element(('jabber:client','presence'))
        self.myroom = "nwws@%s" % (
                common.settings.get('nwws_xmpp_muc', 'conference.esd-nwws-oi.weather.gov'),)
        presence['to'] = "%s/nwws-oi" % (self.myroom,)
        self.xmlstream.send(presence)
        # Whitespace ping to keep our connection happy
        lc = LoopingCall(self.keepalive)
        lc.start(60)
        self.xmlstream.addObserver(STREAM_END_EVENT, lambda _: lc.stop())

        # Track room usage
        rlc = LoopingCall(self.roomlog)
        rlc.start(600)
        self.xmlstream.addObserver(STREAM_END_EVENT, lambda _: rlc.stop())

    def roomlog(self):
        """ Print out the number of users in the rooms we are in """
        for room in self.roominfo:
            log.msg("room %s has %s occupants" % (room, 
                                                  self.roominfo[room]['count']))

    def keepalive(self):
        """
        Send whitespace ping to the server every so often
        TODO: Convert this to use xmpp-ping someday.
        """
        self.xmlstream.send(' ')

    def _disconnect(self, xs):
        """
        Called when we are disconnected from the server, I guess
        """
        log.msg("SETTING authenticated to false!")
        self.authenticated = False

    def sendMessage(self, body, html, xtra):
        """
        Send a message to nwsbot.  This message should have
        @param body plain text variant
        @param html html version of the message
        @param xtra dictionary of stuff that tags along
        """
        if not self.authenticated:
            log.msg("No Connection, Lets wait and try later...")
            reactor.callLater(3, self.sendMessage, body, html, xtra)
            return
        message = domish.Element(('jabber:client','message'))
        message['to'] = self.myroom
        message['type'] = 'groupchat'

        # message.addElement('subject',None,subject)
        message.addElement('body',None,body)
        h = message.addElement('html','http://jabber.org/protocol/xhtml-im')
        b = h.addElement('body', 'http://www.w3.org/1999/xhtml')
        b.addRawXml( html or body )
        # channels is of most important
        x = message.addElement('x', 'nwws-oi')
        for key in xtra.keys():
            if key not in ['payload']:
                x[key] = xtra[key]
            else:
                x.addRawXml('<![CDATA[%s]]>' % (xtra[key],))
        self.xmlstream.send(message)

    def debug(self, elem):
        """
        Debug method
        @param elem twisted.works.xish
        """
        log.msg( elem.toXml().encode('utf-8') )

    def rawDataInFn(self, data):
        """
        Debug method 
        @param data string of what was received from the server
        """
        log.msg('RECV %s' % (unicode(data,'utf-8','ignore').encode('ascii', 'replace'),))

    def rawDataOutFn(self, data):
        """
        Debug method
        @param data string of what data was sent
        """
        if (data == ' '): return 
        log.msg('SEND %s' % (unicode(data,'utf-8','ignore').encode('ascii', 'replace'),))


def shutdown():
    """ Shut myself down, gracefully """
    log.msg("shutdown() called...")
    reactor.callWhenRunning(reactor.stop)

def killer():
    """
    Shut this thing down every day around 12z
    """
    now = datetime.datetime.utcnow()
    z12 = now
    if now.hour >= 12:
        z12 = z12 + datetime.timedelta(days=1)
    z12 = z12.replace(hour=12, minute=0)
    delta = (z12-now).seconds
    log.msg("Will restart in %.1f seconds" % (delta,))
    reactor.callLater( delta, shutdown)


log.msg("Starting NWS Processor")
myJid = jid.JID('%s@%s/nwws_%s' % (
                common.settings.get('nwws_ingest_user', 'nwws_ingest'),
                common.settings.get('nwws_xmpp_domain', 'esd-nwws-oi.weather.gov'),
                datetime.datetime.now().strftime("%Y%m%d%H%M%S") ) )
factory = jclient.basicClientFactory(myJid,
                    common.settings.get('nwws_ingest_user_password', 'nwws_ingest')                 
                                     )

jabber = JabberClient(myJid)

factory.addBootstrap('//event/stream/authd', jabber.authd)
factory.addBootstrap("//event/client/basicauth/invaliduser", jabber.debug)
factory.addBootstrap("//event/client/basicauth/authfailed", jabber.debug)
factory.addBootstrap("//event/stream/error", jabber.debug)
factory.addBootstrap(xmlstream.STREAM_END_EVENT, jabber._disconnect )

log.msg("Attempting to connect to openfire on host: %s port: 5222" % (
     common.settings.get('nwws_xmpp_connect_host', '127.0.0.1')))
reactor.connectTCP(common.settings.get('nwws_xmpp_connect_host', '127.0.0.1'), 
                   5222, factory)

ldmbridge.LDMProductFactory( MyProductIngestor(dedup=True) )

killer()
reactor.run()
