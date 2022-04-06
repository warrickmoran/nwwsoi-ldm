import logging

import slixmpp
from slixmpp.xmlstream import ElementBase, register_stanza_plugin
from slixmpp.stanza import Message
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath
import slixmpp.features.feature_mechanisms as features_mechanisms
import slixmpp.features.feature_starttls as features_starttls
import slixmpp.features.feature_bind as features_bind
import slixmpp.features.feature_session as features_session
import slixmpp.features.feature_rosterver as features_rosterver
import slixmpp.features.feature_preapproval as features_preapproval


import slixmpp.plugins.xep_0030 as xep_0030
import slixmpp.plugins.xep_0045 as xep_0045
import slixmpp.plugins.xep_0199 as xep_0199
import slixmpp.plugins.xep_0004 as xep_0004
import slixmpp.plugins.xep_0092 as xep_0092
from helpers.nww_oi_muc_stanza import X as CustomStanza

import ssl

import multiprocessing
import asyncio


class MUCBot(slixmpp.ClientXMPP):

    def __init__(self, jid: slixmpp.JID, password, room="nwws@conference.esd-nwws-oi.weather.gov/nwws-oi"):
        slixmpp.ClientXMPP.__init__(self, jid.full, password)

        self.room = room
        self.nick = "OPPSD.SEIT.OIMONITOR-{}/v1.0(http://n.a;warrick.moran@noaa.gov)".format(jid.user)
        self.server_url = jid.server
        self.password = password
        

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self._start)

        self.add_event_handler("message", self._message)

        self.add_event_handler("connected", self._connected)

        self.add_event_handler("connection_failed", self._connection_failed)

        self.add_event_handler("disconnected", self._disconnected)

        # If you are working with an OpenFire server, you will
        # need to use a different SSL version:
        #self.ssl_version = ssl.PROTOCOL_TLSv1_2 

        register_stanza_plugin(Message, CustomStanza)
        self.configure()

    def configure(self):
        features_starttls.STARTTLS.name

        features_bind.FeatureBind.name

        self[features_mechanisms.FeatureMechanisms.name].unencrypted_plain = True

        #logging.info("features: {}".format(list(xmpp)))

        self.register_plugin(xep_0030.XEP_0030.name)  # Service Discovery

        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin(
            'xep_0199', {'keepalive': True, 'interval': 300, 'timeout': 5})  # XMPP Ping


    async def _start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        await self.get_roster()
        self.send_presence()
        self.plugin['xep_0045'].join_muc(self.room,
                                         self.nick,
                                         password=self.password)
        logging.info("Entered Chat Room: {}".format(self.room))
        #self.queue = MUCBotQueue()
        #self.queue._queue_initialize()

    def _message(self, msg):
        """
        Process incoming message stanzas from any chat room. Be aware
        that if you also have any handlers for the 'message' event,
        message stanzas may be processed by both handlers, so check
        the 'type' attribute when using a 'message' event handler.

        Whenever the bot's nickname is mentioned, respond to
        the message.

        IMPORTANT: Always check that a message is not from yourself,
                   otherwise you will create an infinite loop responding
                   to your own messages.

        This handler will reply to messages that mention
        the bot's nickname.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['mucnick'] != self.nick:
            logging.debug("{0}".format(msg['body']))

    def _connected(self, msg):
        logging.info("Connected {0}".format(msg))

    def _connection_failed(self, msg):
        logging.info("Connection Failed {0}".format(msg))

    def _disconnected(self, msg):        logging.info("Disconnected {0}".format(msg))


class MUCBotQueue(multiprocessing.Process):
    def __init__(self, messageQueue:multiprocessing.JoinableQueue, jid: slixmpp.JID, password, url=None) -> None:
        multiprocessing.Process.__init__(self)

        # get a new event loop
        self.loop = asyncio.new_event_loop()

        # set the event loop for the current thread
        asyncio.set_event_loop(self.loop)

        self.queue = messageQueue
        self.jid = jid
        self.url = url
        self.xmpp = MUCBot(self.jid, password)

    def run(self) -> None:
        if (self.url == None):
            self.xmpp.connect((self.jid.full, 5222), use_ssl=False)
        else:
            self.xmpp.connect((self.url, 5222), use_ssl=False)
        self.xmpp.process()  

        self.loop.close()

    
if __name__ == "__main__":
    from socket import gethostname
    import coloredlogs

    logging.basicConfig(level=logging.DEBUG)
    coloredlogs.install(level=logging.DEBUG)

    type = "DEV"

    if type == "LIVE":
        xmpp = MUCBot(slixmpp.JID("######@conference.nwws-oi.weather.gov/nwws-oi"), "########")

        xmpp.connect(("nwws-oi.weather.gov", 5222), use_ssl=False)
        
        xmpp.process()
    else:
        xmpp = MUCBotQueue(None, slixmpp.JID("nwws_ingest@conference.esd-nwws-oi.weather.gov/nwws"), "nwws_ingest", "esd-nwws-oi.weather.gov")
        #xmpp.connect(("esd-nwws-oi.weather.gov", 5222), use_ssl=False)
        xmpp.start()
        xmpp.join()

