from argparse import ONE_OR_MORE
from queue import Empty
import subprocess
import os
import logging
import re
import psutil

from slixmpp.stanza import Message
from slixmpp.xmlstream import ElementBase, register_stanza_plugin
from helpers.nww_oi_muc_stanza import X as CustomStanza
from slixmpp.xmlstream.matcher import StanzaPath
from slixmpp.xmlstream.handler import Callback

import asyncio

from datetime import datetime


class MucBotLDMEncoder:
    """
    A simple LDM encoder that executes the pqinsert utility 
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, client, activate=False):
        self.activate = activate
        self.count = 0
        self.slixmpp_client = client
        self.queue = None

        self.PQINSERT_CMD = "/home/ldm/bin/pqinsert"
        self.REGEX = "(\d\d\d\s+)(.*)"

        self._slixmpp_initialize()

        if not self.activate:
            logging.warning("Send To LDM Disabled")

    async def _queue_initialize(self):
        self.queue = asyncio.Queue()
        asyncio.create_task(self.consume("Message Ingest", self.queue))
        await self.queue.join()

    def _slixmpp_initialize(self):
        #self.slixmpp_client.register_stanza_plugin(Message, CustomStanza)
        self.slixmpp_client.register_handler(Callback('NWWS-OI/X Message', StanzaPath('{%s}message/{%s}x' % (self.slixmpp_client.default_ns,self.slixmpp_client.default_ns)),self._message))
        self.slixmpp_client.add_event_handler('_custom_handle_x', self._handle_x_event)

    def _message(self, msg):
        if msg['mucnick'] != self.slixmpp_client.nick:
            cccc = msg['x'].xml.attrib['cccc']
            ttaaii = msg['x'].xml.attrib['ttaaii']
            issue = msg['x'].xml.attrib['issue']
            awipsid = msg['x'].xml.attrib['awipsid']
            content = msg['x'].xml.text
        
            logging.info("Product Content: {} {} {} {}".format(ttaaii,cccc,issue,awipsid))

            if (self.activate):
                self.slixmpp_client.event('_custom_handle_x', (ttaaii,cccc,awipsid,content))

    async def _handle_x_event(self, msg):
        if (self.queue == None):
            await self._queue_initialize()

        await self.queue.put(msg)

    async def consume(self, name, q: asyncio.Queue) -> None:
        while True:
            product = await q.get()
            logging.debug("Consumer {0} got element <{1}>".format(name, product))
           
            self.sendToLDM(product)
            
            q.task_done()

    def sendToLDM(self, product):
        if self.activate:
            now = datetime.now()
            filename = "/tmp/{}-{}-{}".format(
                product[0], product[1], product[2])
            productId = "{0} {1}".format(product[0], now.strftime("%H%M%S"))

            try:
                if (self.writeTmpFile(filename, product[3]) == True):
                    # insert product into LDM queue using product id format: t1t2a1a2 MMHHSS
                    push_status = subprocess.run([self.PQINSERT_CMD, "-f", "WMO", "-l",
                                                  "/home/ldm/var/log", "-v", "-p",
                                                  "{0}".format(productId), filename], timeout=5)
                    sig_status = self.sendSigCont()
                    self.count += 1
                    if ((push_status.returncode == 0) and sig_status):
                        logging.info(
                            "Successful push of {0} into LDM Queue".format(productId))
                    else:
                        logging.error(
                            "UnSuccessful push of {0} into LDM Queue".format(productId))

                else:
                    logging.error("Unable to Write Product to Disk")

                self.deleteTmpFile(filename)
            except subprocess.SubprocessError as err:
                logging.error("Send To LDM Processing Error: {0}".format(err))
            except FileNotFoundError as err:
                logging.error(
                    "Send To LDM Unable to Find {0} Command".format(self.pqingest_cmd))
            except Exception as err:
                logging.error("Unhandled Exception {0}".format(err))

    def writeTmpFile(self, filename, content):
        try:
            file = open(filename, 'w')

            stripContent = self.stripTrackingNumber(content)

            logging.info("{}: {}".format(filename, stripContent))

            file.write(stripContent)

            # Closing file
            file.close()
        except:
            logging.error("Write Temp File Exception")
            return False

        return True

    def deleteTmpFile(self, filename):
        if os.path.exists(filename):
            os.remove(filename)
            return True
        return False

    def stripTrackingNumber(self, content):
        match = re.search(self.REGEX, content, re.DOTALL)
        if match:
            if match.group(2) != None:
                return match.group(2)

        return content

    def sendSigCont(self):
        procObjList = [procObj for procObj in psutil.process_iter(
        ) if 'ldmd' in procObj.name().lower()]

        if (len(procObjList) > 0):
            # LDMD needs to be notified of an incoming product
            # Send SigCont (18)
            try:
                os.kill(procObjList[0].pid, 18)
                logging.info("Notifying LDMD: {}".format(procObjList[0].pid))
                return True
            except Exception as err:
                logging.error("Unable to Send SigCont {0}".format(err))

        logging.error("Unable to Notify LDMD")

        return False
