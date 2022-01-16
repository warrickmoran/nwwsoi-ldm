'''
Created on Nov 5, 2019

@author: warrick.moran
'''
import sleekxmpp
import logging
import socket
from sleekxmpp.exceptions import IqError, IqTimeout
from threading import Timer
from nww_oi_muc_stanza import X as Stanza
from sleekxmpp.xmlstream.stanzabase import register_stanza_plugin
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp import Message

# Create a custom logger
logger = logging.getLogger(__name__)

class MUCBot(sleekxmpp.ClientXMPP):
    """
    A simple SleekXMPP bot that will greets those
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, jid, password, room, nick, OI_URL):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        #sleekxmpp.ssl_version = ssl.PROTOCOL_SSLv3

        self.jid
        self.room = room
        self.nick = "OPPSD.SEIT.OIMONITOR-{}/v1.0(http://n.a;warrick.moran@noaa.gov)".format(nick)
        self.url = OI_URL
        
        register_stanza_plugin(Message, Stanza)
        self.registerHandler(Callback('NWWS-OI/X Message', StanzaPath('{%s}message/{%s}x' % (self.default_ns,self.default_ns)),self.onX))

        
        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start, threaded=True)

        # The groupchat_message event is triggered whenever a message
        # stanza is received from any chat room. If you also also
        # register a handler for the 'message' event, MUC messages
        # will be processed by both handlers.
        #self.add_event_handler("groupchat_message", self.muc_message)
        self.add_event_handler("custom_action", self.muc_message)
        
        self.add_event_handler("presence_available", self.muc_online)
        
        self.add_event_handler("presence_unavailable", self.muc_offline)
        self.add_event_handler("presence_unsubscribed", self.muc_offline)
        
        self.add_event_handler("roster_update", self.muc_roster_update)
        
        self.add_event_handler("connected", self.muc_connected)
        self.add_event_handler("disconnected", self.muc_disconnected)
        
        self.add_event_handler("Ping", self.ping_xmpp)
        
        self.member_list = []
        self.member_list_prev = []
        self.member_list_complete = False
        self.product_count = 0
        

    def onX(self, msg):
        self.event('custom_action', msg)
        logger.debug("Received Custom Action: {}".format(msg))

    def start(self, event):
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
        logger.info("Session Started: {}".format(event))
        
        self.get = ''
        # Values to control which disco entities are reported
        self.info_types = ['', 'all', 'info', 'identities', 'features']
        self.identity_types = ['', 'all', 'info', 'identities']
        self.feature_types = ['', 'all', 'info', 'features']
        self.items_types = ['', 'all', 'items']
        
        self.get_roster()
        self.send_presence()
    
        self.plugin['xep_0045'].joinMUC(self.room,
                                        self.nick,
                                        wait=True)
                                        # If a room password is needed, use:
                                        # password=the_room_password)
        logger.info("Joined MUC Room: {}".format(self.room))  
                                     
        Timer(10, self.ping_xmpp, ()).start()
        
        try:
            if self.get in self.info_types:
                # By using block=True, the result stanza will be
                # returned. Execution will block until the reply is
                # received. Non-blocking options would be to listen
                # for the disco_info event, or passing a handler
                # function using the callback parameter.
                info = self['xep_0030'].get_info(jid=self.url,
                                                 node='',
                                                 block=True)
            if self.get in self.items_types:
                # The same applies from above. Listen for the
                # disco_items event or pass a callback function
                # if you need to process a non-blocking request.
                items = self['xep_0030'].get_items(jid=self.url,
                                                   node='',
                                                   block=True)
            else:
                logger.error("Invalid disco request type.")
                return
        except IqError as e:
            logging.error("Entity returned an error: %s" % e.iq['error']['condition'])
        except IqTimeout:
            logging.error("No response received.")
        else:
            header = 'XMPP Service Discovery: %s' % self.url
            logger.debug(header)
            logger.debug('-' * len(header))
            #if self.target_node != '':
            #    print('Node: %s' % self.url)
            #    print('-' * len(header))

            if self.get in self.identity_types:
                logger.debug('Identities:')
                for identity in info['disco_info']['identities']:
                    logger.debug('  - %s' % str(identity))

            if self.get in self.feature_types:
                logger.debug('Features:')
                for feature in info['disco_info']['features']:
                    logger.debug('  - %s' % feature)

            if self.get in self.items_types:
                logger.debug('Items:')
                for item in items['disco_items']['items']:
                    logger.debug('  - %s' % str(item))
                    
    def muc_connected(self, event):
        logger.info("Connected")
        
    def muc_disconnected(self, event):
        logger.info("Disconnected")
        self.member_list.clear()
    
    def muc_message(self, msg):
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
        #if msg['mucnick'] != self.nick and self.nick in msg['body']:
        #    self.send_message(mto=msg['from'].bare,
        #                      mbody="I heard that, %s." % msg['mucnick'],
        #                      mtype='groupchat')
        #print("Received Message: {}".format(msg['body']))
        self.product_count += 1
        cccc = msg['x'].xml.attrib['cccc']
        ttaaii = msg['x'].xml.attrib['ttaaii']
        issue = msg['x'].xml.attrib['issue']
        awipsid = msg['x'].xml.attrib['awipsid']
        content = msg['x']['body']
        logger.info("Product Content: {} {} {} {} \n {}".format(ttaaii,cccc,issue,awipsid,content))

    def muc_online(self, presence):
        """
        Process a presence stanza from a chat room. In this case,
        presences from users that have just come online are
        handled by sending a welcome message that includes
        the user's nickname and role in the room.

        Arguments:
            presence -- The received presence stanza. See the
                        documentation for the Presence stanza
                        to see how else it may be used.
        """
        logger.debug("Online {}".format(presence['from']))
        if not presence['from'].__str__() in self.member_list:
            self.member_list.append(presence['from'].__str__())
            logger.debug("{},{},{}".format(socket.gethostbyname(self.url),len(self.member_list),self.member_list))
            
    def muc_offline(self, presence):
        logger.debug("Offline {}".format(presence['from']))
        
        if presence['from'].__str__() in self.member_list:
                self.member_list.remove(presence['from'].__str__())
                logger.debug("{},{},{}".format(socket.gethostbyname(self.url),len(self.member_list),self.member_list))
        
    def muc_roster_update(self, roster):
        logger.info("Roster Update:{}".format(self.roster))
        result = self['xep_0030'].get_items(jid="conference.nwws-oi.weather.gov", iterator=True)

        for room in result['disco_items']:
            logger.info("Found room %s, jid is %s" % (room, room['jid']))
            
    def ping_xmpp(self):
        try:
            member_list_new = list(set(self.member_list_prev) - set(self.member_list))
              
            if((len(member_list_new) > 0) or (len(self.member_list_prev) == 0)):
                logger.info("{},{},{}".format(socket.gethostbyname(self.url),len(self.member_list),self.member_list))
                #logger.debug("{},{},{}".format(socket.gethostbyname(self.url),len(self.member_list),self.member_list))
                if (len(member_list_new) > 0):
                    logger.info("{},diff-{}".format(socket.gethostbyname(self.url),member_list_new))
            else:
                logger.debug("{},{},{}".format(socket.gethostbyname(self.url),len(self.member_list),self.member_list))
     
        except IqError as e:
            logger.error("{}, Error pinging: {}".format(socket.gethostbyname(self.url), e.iq['error']['condition']))
            del self.member_list[:]
 
        except IqTimeout:
            logger.error("{}, No response from {}".format(socket.gethostbyname(self.url), e.iq['error']['condition']))
            del self.member_list[:]

            
        self.member_list_prev = self.member_list.copy()

        Timer(300, self.ping_xmpp, ()).start()

        
