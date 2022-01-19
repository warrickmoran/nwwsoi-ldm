from argparse import ONE_OR_MORE
from queue import Empty
import subprocess
import os
import logging
import re
import psutil
import signal

from datetime import datetime


class MucBotLDMEncoder:
    """
    A simple LDM encoder that executes the pqinsert utility 
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, activate=False):
        self.activate = activate
        self.count = 0

        self.PQINSERT_CMD = "/home/ldm/bin/pqinsert"
        self.REGEX = "(\d\d\d\s+)(.*)"

        if not self.activate:
            logging.warning("Send To LDM Disabled")

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
