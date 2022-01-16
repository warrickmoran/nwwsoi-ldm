import subprocess
import os
import logging

class MucBotLDMEncoder:
    """
    A simple LDM encoder that executes the pqinsert utility 
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, pqingest_cmd):
        self.pqingest_cmd = pqingest_cmd
        self.count = 0
        
        if self.pqingest_cmd == None:
            logging.warning("Send To LDM Disabled")

    def sendToLDM(self, product):
        if self.pqingest_cmd != None:
            filename = "/tmp/{}-{}-{}".format(product[0],product[1],product[2])
        
            try:
                if (self.writeTmpFile(filename, product[3]) == True):
        
                    status = subprocess.run([self.pqingest_cmd,"-s {0}".format(self.count),"-f WMO", "-i", filename],timeout=5)
        
                    if (status.returncode == 0):
                        logging.info("Successful push of {0} into LDM Queue".format(filename))
                    else: 
                        logging.error("UnSuccessful push of {0} into LDM Queue".format(filename))
                else:
                    logging.error("Unable to Write Product to Disk")
            except subprocess.SubprocessError as err:
                logging.error("Send To LDM Processing Error: {0}".format(err))
            except FileNotFoundError as err:
                logging.error("Send To LDM Unable to Find {0} Command".format(self.pqingest_cmd))
        
    def writeTmpFile(self, filename, content):
        try:
            file = open(filename, 'w')
  
            # Writing a string to file
            file.write(content)
  
            # Closing file
            file.close()
        
            if os.path.exists(filename):
                os.remove(filename)
                return True
        except:
            logging.error("Write Temp File Exception")
            
        return False
        


    