from email import contentmanager
import logging
import asyncio

import slixmpp
from slixmpp.xmlstream import ElementBase, register_stanza_plugin
from slixmpp.stanza import Message
from slixmpp.xmlstream.handler import Callback
from slixmpp.xmlstream.matcher import StanzaPath
from nww_oi_muc_stanza import X as CustomStanza

import nwws_oi_ldm_encoder as LdmEncoder


class MUCBot(slixmpp.ClientXMPP):

    def __init__(self, jid, password, room, nick, server_url, queue, ldmcmd=None):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.room = room
        self.nick = "OPPSD.SEIT.OIMONITOR-{}/v1.0(http://n.a;warrick.moran@noaa.gov)".format(nick)
        self.server_url = server_url
        self.ldmcmd = ldmcmd
        self.queue = queue

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
        #self.ssl_version = ssl.PROTOCOL_SSLv3

        register_stanza_plugin(Message, CustomStanza)
        self.register_handler(Callback('NWWS-OI/X Message', StanzaPath('{%s}message/{%s}x' % (self.default_ns,self.default_ns)),self._handle_x))
        self.add_event_handler('_custom_handle_x', self._handle_x_event)

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
        
        
        self.ldm_encoder = LdmEncoder.MucBotLDMEncoder("pqingest")
        asyncio.create_task(self.consume("Message Ingest", self.queue))
        await self.queue.join()

    async def _handle_x_event(self, msg):
        await self.queue.put(msg)
        
    async def consume(self, name, q: asyncio.Queue) -> None:
        while True:
            product = await q.get()
            logging.info("Consumer {0} got element <{1}>".format(name, product))
           
            self.ldm_encoder.sendToLDM(product)
            
            q.task_done()

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
    
    def _handle_x(self, msg):
        if msg['mucnick'] != self.nick:
            cccc = msg['x'].xml.attrib['cccc']
            ttaaii = msg['x'].xml.attrib['ttaaii']
            issue = msg['x'].xml.attrib['issue']
            awipsid = msg['x'].xml.attrib['awipsid']
            content = msg['x'].xml.text
        
            logging.info("Product Content: {} {} {} {}".format(ttaaii,cccc,issue,awipsid))

            self.event('_custom_handle_x', (ttaaii,cccc,awipsid,content))

    def _connected(self, msg):
        logging.info("Connected {0}".format(msg))

    def _connection_failed(self, msg):
        logging.info("Connection Failed {0}".format(msg))

    def _disconnected(self, msg):
        logging.info("Disconnected {0}".format(msg))
