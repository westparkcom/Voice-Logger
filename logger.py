#################################################################
#                                                               #
# Copyright (c) 2016 Westpark Communications, L.P.              #
# Subject to the GNU Affero GPL license                         #
# See the file LICENSE.md for details                           #
#                                                               #
#################################################################
import SocketServer
import threading
from datetime import date, datetime
import time
import sys
import socket
import os
import ConfigParser
import logging
import logging.config
import random
import ESL
import json
import pwd
import grp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Get config and logging info from CLI args
i = 0
argsDict = {}
for item in sys.argv:
    if i == 0:
        i = i + 1
        pass
    else:
        i = i + 1
        paramname, paramval = item.partition("=")[::2]
        argsDict[paramname] = paramval

try:
    loggerLogConfigFile = argsDict['--logconfig']
except:
    print ""
    print "Error: log configuration file location not specified."
    print ""
    print "Usage: python", sys.argv[0], "--config=/path/to/configfile/loggerconfig.ini --logconfig=/path/to/logconfigfile/loggerlog.ini"
    sys.exit(1)
try:
    loggerConfigFile = argsDict['--config']
except:
    print ""
    print "Error: log configuration file location not specified."
    print ""
    print "Usage: python", sys.argv[0], "--config=/path/to/configfile/loggerconfig.ini --logconfig=/path/to/logconfigfile/loggerlog.ini"
    sys.exit(1)
        
# Global config
config = ConfigParser.ConfigParser()
config.read(loggerConfigFile)

# Logging setup
logging.config.fileConfig(loggerLogConfigFile)
logwrite = logging.getLogger('loggerLog')

class listenerService(SocketServer.BaseRequestHandler):

    """
    'Thread handler. We only need one thread per connection
    'As PInnacle keeps the connection open and each instance
    'Only deals with one call at a time
    """

    def handle(self):
        """
        Listens for requests from PInnacle client and sends them to other
        functions for processing, then sends return value to client
        as a response
        
        Args:
            self: This class
        """
        try:
            data = 'dummy'
            logwrite.info("%s: Client connected from address %s:%s" %
                          (str(threading.current_thread().ident), self.client_address[0], str(self.client_address[1])))
            while len(data):
                self.request.settimeout(
                    int(config.get('Network', 'TCPTIMEOUT')))
                data = self.request.recv(4096)
                logwrite.debug("%s: Received data: %s" %
                               (str(threading.current_thread().ident), data))
                cleandata = data.strip()
                # Send what we received off to be processed
                response = self.RequestHandler(cleandata)
                self.request.send(response)
            logwrite.info("%s: Client %s:%s disconnected" %
                          (str(threading.current_thread().ident), self.client_address[0], str(self.client_address[1])))
            self.request.close()
            return
        except(socket.timeout, socket.error, threading.ThreadError, Exception) as e:
            if str(e) == 'timed out':
                logwrite.info("%s: Connection %s for client %s:%s" %
                          (str(threading.current_thread().ident), str(e), self.client_address[0], str(self.client_address[1])))
            else:
                logwrite.error("%s: Error: %s" %
                          (str(threading.current_thread().ident), str(e)))
            self.request.close()
            return
            
    def RequestHandler(self, RequestData):
        """ Handles request from PInnacle and determines how to process them
        
        Takes the data we received in the handle function and determines
        what we should do with it. There are currently 5 menthods we are
        aware of that PInnacle client sends:
            START(agentID,fldClientID=XXXX,fldDNIS=XXXXXXXXXX,fldANI=XXXXXXXXXX,fldCallType=X,fldCSN=XXXXXXX,fldAgentLoginID=XXX)
            STOP(agentID)
            PAUSE(agentID)
            RESUME(agentID)
            HELLO ()
            
        Args:
            self: This class
            RequestData: the request sent by PInnacle client
        """
        
        if ('(' not in RequestData) or (')' not in RequestData):
            logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
            respresult = "ERROR(NOT VALID COMMAND)\r\n"
            logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
            return respresult
        if RequestData[0:5] == "START":
            callParams = self.Parse(RequestData[5:])
            if 'BADDATA' in callParams:
                logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            originateResult = self.OriginateRecording(callParams)
            if originateResult[0] == False:
                respresult = "ERROR(NOT RECORDING)\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            elif originateResult[0] == True:
                respresult = originateResult[1] + "\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
        elif RequestData[0:4] == "STOP":
            callParams = self.Parse(RequestData[4:])
            if 'BADDATA' in callParams:
                logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            recstop = self.StopRecording(callParams['agentID'])
            if recstop[0] == True:
                respresult = "OK\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            else:
                respresult = "ERROR(" + recstop[1] + ")\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
        elif RequestData[0:5] == "PAUSE":
            callParams = self.Parse(RequestData[5:])
            if 'BADDATA' in callParams:
                logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            recpaused = self.PauseResumeRecording(callParams['agentID'], "mask")
            if recpaused[0] == True:
                respresult = "OK\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            else:
                respresult = "ERROR(" + recpaused[1] + ")\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
        elif RequestData[0:6] == "RESUME":
            callParams = self.Parse(RequestData[6:])
            if 'BADDATA' in callParams:
                logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            recresume = self.PauseResumeRecording(callParams['agentID'], "unmask")
            if recresume[0] == True:
                respresult = "OK\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
            else:
                respresult = "ERROR(" + recresume[1] + ")\r\n"
                logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
                return respresult
        elif RequestData[0:5] == "HELLO":
            now = datetime.now()
            helloStr = "OK " + str(now.strftime("%m/%d/%Y %I:%M:%S %p")) + " Calls: " + str(random.randint(0, 999999)) + "\r\n"
            logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), helloStr))
            return helloStr
        else:
            logwrite.warning("%s: Invalid command received: %s" % (str(threading.current_thread().ident), RequestData))
            respresult = "ERROR(NOT VALID COMMAND)\r\n"
            logwrite.debug("%s: Responding with: %s" % (str(threading.current_thread().ident), respresult))
            return respresult
            
    def Parse(self, CallParameters):
        """ Parses the START() command parameters and returns a dictionary
        
        Splits out all the parameters received from PInnacle. All but the first
        parameter are in K=V format separated by commas. Returns a dictionary
        with all the K,V pairs
        
        Args:
            self: This class
            CallParameters: Raw string of the parameters (parenthesis included)
        """
        
        # Remove outer parenthesis
        if not ((CallParameters[0] == '(') or (CallParameters[-1] == ')')):
            return {'BADDATA': False}
        cleanParameters = CallParameters[1:-1]
        parametersArr = cleanParameters.split(",")
        i = 0
        paramsDict = {}
        for item in parametersArr:
            #First parameter we receive isn't in K,V pair, so make a key...
            if i == 0:
                paramsDict['agentID'] = item
            else:
                name, var = item.partition("=")[::2]
                paramsDict[name] = var.rstrip()
            i = i + 1
        return paramsDict
    
    def PauseResumeRecording(self, agentID, action):
        """ Pauses or resumes the recording in FreeSWITCH
        
        Gets a list of active recordings from FreeSWITCH and iterates
        through them, checking each agent_id variable for each call to see if
        that call matches. If there's a match, pause/resume the recording
        and return [True, "OK"]. If no match, return [False, "NOT RECORDING"].
        If there's an error, return [False, "INTERNAL ERROR"]
        
        Args:
            self: This class
            agentID: (string) The agentID to check against
            action: (string) 'mask' (pause) or 'unmask' (resume)
        """
        
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():
            calls = fscon.api("show", "channels as json")
            CurrentCalls = json.loads(calls.getBody())
            j = 0
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug("%s: Checking UUID %s for agent ID %s..." % (str(threading.current_thread().ident), str(row['call_uuid']), str(agentID)))
                    varstring = str(row['call_uuid']) + " agent_id"
                    pausearrstring = str(row['call_uuid']) + " pausearr"
                    startepochstring = str(row['call_uuid']) + " answered_time"
                    fsreturn = fscon.api("uuid_getvar", varstring)
                    fsreturn2 = fscon.api("uuid_getvar", pausearrstring)
                    fsreturn3 = fscon.api("uuid_getvar", startepochstring)
                    retAgentID = fsreturn.getBody().strip()
                    retPauseArr = fsreturn2.getBody().strip()
                    retStartEpoch = fsreturn3.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn("%s: Call for agent ID %s found, %s recording for %s..." % (str(threading.current_thread().ident), str(agentID), str(action), str(row['call_uuid'])))
                        filestring = str(row['call_uuid']) + " recording_file"
                        filereturn = fscon.api("uuid_getvar", filestring)
                        filename = filereturn.getBody().strip()
                        output = fscon.api("uuid_record", str(row['call_uuid']) + " " + action + " " + str(filename))
                        logwrite.debug("%s: FreeSWITCH output: %s" % (str(threading.current_thread().ident), output.getBody().strip()))
                        pausestring = str(row['call_uuid']) + " recording_paused 1"
                        fscon.api("uuid_setvar", pausestring)
                        logwrite.debug("%s: Current epoch time: %s" % (str(threading.current_thread().ident), str(time.time())))
                        logwrite.debug("%s: Call start epoch time: %s" % (str(threading.current_thread().ident), str(retStartEpoch)[:10]))
                        prtime = int(time.time()) - int(str(retStartEpoch)[:10])
                        if action == "mask":
                            prechar = "PAUSE>>"
                        else:
                            prechar = "START>>"
                        pausetimes = retPauseArr + "|:" + prechar + str(prtime)
                        pausetimestr = str(row['call_uuid']) + " pausearr " + pausetimes
                        fscon.api("uuid_setvar", pausetimestr)
                        j = j + 1
                        time.sleep(.33)
            except (Exception) as e:
                if str(e) == "'rows'":
                    logwrite.debug("%s: No active recordings found for agent ID: %s" % (str(threading.current_thread().ident), str(agentID)))
                else:
                    logwrite.error("%s: Exception encountered: %s" % (str(threading.current_thread().ident), e))
                fscon.disconnect()
                return [False, "NOT RECORDING"]
            fscon.disconnect()
            if j == 0:
                return [False, "NOT RECORDING"]
            else:
                return [True, "OK"]
        else:
            logwrite.error("%s: Unable to connect to FreeSWITCH to %s call, responding with ERROR" % (str(threading.current_thread().ident), str(action)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger %s failure for agent ID: %s" % (str(action), str(agentID))
                emailMessage = "Unable to connect to FreeSWITCH to %s recording for agent ID: %s." % (str(action), str(agentID))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            return [False, "INTERNAL ERROR"]
    
    def StopRecording(self, agentID):
        """ Stops the recording in FreeSWITCH
        
        Gets a list of active recordings from FreeSWITCH and iterates
        through them, checking each agent_id variable for each call to see if
        that call matches. If there's a match, stop the recording
        and return [True, "OK"]. If no match, return [False, "NOT RECORDING"].
        If there's an error, return [False, "INTERNAL ERROR"]
        
        Args:
            self: This class
            agentID: (string) The agentID to check against
        """
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():
            calls = fscon.api("show", "channels as json")
            CurrentCalls = json.loads(calls.getBody())
            j = 0
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug("%s: Checking UUID %s for agent ID %s..." % (str(threading.current_thread().ident), str(row['call_uuid']), str(agentID)))
                    varstring = str(row['call_uuid']) + " agent_id"
                    fsreturn = fscon.api("uuid_getvar", varstring)
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn("%s: Call for agent ID %s found, killing UUID %s..." % (str(threading.current_thread().ident), str(agentID), str(row['call_uuid'])))
                        fscon.api("uuid_kill", str(row['call_uuid']))
                        j = j + 1
                        time.sleep(.33)
            except (Exception) as e:
                if str(e) == "'rows'":
                    logwrite.debug("%s: No active recordings found for agent ID: %s" % (str(threading.current_thread().ident), str(agentID)))
                else:
                    logwrite.error("%s: Exception encountered: %s" % (str(threading.current_thread().ident), e))
                fscon.disconnect()
                return [False, "NOT RECORDING"]
            fscon.disconnect()
            if j == 0:
                return [False, "NOT RECORDING"]
            else:
                return [True, "OK"]
        else:
            logwrite.error("%s: Unable to connect to FreeSWITCH to stop call, responding with ERROR" % (str(threading.current_thread().ident)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger stop failure for agent ID: %s" % (str(agentID))
                emailMessage = "Unable to connect to FreeSWITCH to stop recording for agent: %s" % (str(agentID))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            return [False, "INTERNAL ERROR"]
    
    def checkDuplicateCalls(self, agentID):
        """ Checks for multiple recordings per agentID in FreeSWITCH
        
        Gets a list of active recordings from FreeSWITCH and iterates
        through them, checking each agent_id variable for each call to see if
        that call matches. If there's a match, stop the recordings
        and return True. If no match, return True. If no active recordings,
        return False. If there's a problem, return "ERROR"
        
        Args:
            self: This class
            agentID: (string) The agentID to check against
        """
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api("show", "channels as json")
            CurrentCalls = json.loads(calls.getBody())
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug("%s: Checking UUID %s for agent ID %s..." % (str(threading.current_thread().ident), str(row['call_uuid']), str(agentID)))
                    varstring = str(row['call_uuid']) + " agent_id"
                    fsreturn = fscon.api("uuid_getvar", varstring)
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn("%s: Duplicate call for agent ID %s found: %s..." % (str(threading.current_thread().ident), str(agentID), str(row['call_uuid'])))
                        filevarstring = str(row['call_uuid']) + " recording_file"
                        fsreturn = fscon.api("uuid_getvar", filevarstring)
                        retFile = fsreturn.getBody().strip()
                        filenamestr = retFile.rsplit('/')[-1]
                        fscon.disconnect()
                        return [True, filenamestr]
            except (Exception) as e:
                if str(e) == "'rows'":
                    logwrite.debug("%s: No active recordings found for agent ID: %s" % (str(threading.current_thread().ident), str(agentID)))
                else:
                    logwrite.error("%s: Exception encountered: %s" % (str(threading.current_thread().ident), e))
                fscon.disconnect()
                return [False, False]
        else:
            logwrite.error("%s: Unable to connect to FreeSWITCH to check duplicate calls, responding with ERROR" % (str(threading.current_thread().ident)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger duplicate call check failure for agent ID: %s" % (str(agentID))
                emailMessage = "Unable to connect to FreeSWITCH to check for duplicate recordings for agent: %s" % (str(agentID))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            return [False, False]
            
    def killDuplicateCalls(self, agentID):
        """ Checks for multiple recordings per agentID in FreeSWITCH
        
        Gets a list of active recordings from FreeSWITCH and iterates
        through them, checking each agent_id variable for each call to see if
        that call matches. If there's a match, return [True, recfilename].
        If no match, return True. If no active recordings,
        return False. If there's a problem, return "ERROR"
        
        Args:
            self: This class
            agentID: (string) The agentID to check against
        """
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api("show", "channels as json")
            CurrentCalls = json.loads(calls.getBody())
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug("%s: Checking UUID %s for agent ID %s..." % (str(threading.current_thread().ident), str(row['call_uuid']), str(agentID)))
                    varstring = str(row['call_uuid']) + " agent_id"
                    fsreturn = fscon.api("uuid_getvar", varstring)
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.debug("%s: Duplicate call for agent ID %s found, killing UUID %s..." % (str(threading.current_thread().ident), str(agentID), str(row['call_uuid'])))
                        fscon.api("uuid_kill", str(row['call_uuid']))
                        time.sleep(.33)
            except (Exception) as e:
                if str(e) == "'rows'":
                    logwrite.debug("%s: No calls found..." % (str(threading.current_thread().ident)))
                    fscon.disconnect()
                    return False
                logwrite.debug("%s: Exception encountered:, %s..." % (str(threading.current_thread().ident), e))
                fscon.disconnect()
                return False
            fscon.disconnect()
            return True
        else:
            logwrite.error("%s: Unable to connect to FreeSWITCH to kill call, responding with ERROR" % (str(threading.current_thread().ident)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger recording kill failure for agent ID: %s" % (str(agentID))
                emailMessage = "Unable to connect to FreeSWITCH to kill duplicate recording for agent: %s" % (str(agentID))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            return "ERROR"
            
    def checkGateways(self, gatewayName, maxCalls):
        """ Checks to see if gateway is free to use
        
        Gets limit usage and returns True if gateway is available, False if
        at maximum capacity, or False if cannot connect to FreeSWITCH
        
        Args:
            self: This class
            gatewayName: Name of the FreeSWITCH gateway to check
            maxCalls: maximum number of calls allowed on the gateway
        """
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api("limit_usage", "hash logger gw_" + str(gatewayName))
            currentCalls = calls.getBody()
            fscon.disconnect()
            if int(currentCalls) < int(maxCalls):
                logwrite.debug("%s: Gateway %s is currently at %s which is under MAXCALLS threshold of %s, using this gateway" % (str(threading.current_thread().ident), str(gatewayName), str(currentCalls), str(maxCalls)))
                return True
            else:
                logwrite.debug("%s: Gateway %s is currently at %s which is over MAXCALLS threshold of %s, skipping this gateway" % (str(threading.current_thread().ident), str(gatewayName), str(currentCalls), str(maxCalls)))
                return False
        else:
            return False
    
    def OriginateRecording(self, CallData):
        """ Starts recording call
        
        Sends command to FreeSWITCH to begin recording call. Checks
        to see if there is already an active recording for the agentID
        and stops if exists. 
        
        Args:
            self: This class
            CallData: (string) The data received from PInnacle that is parsed
                to start the recording
        """
        
        if not 'fldDNIS' in CallData:
            logwrite.debug("%s: Park resume request received, filling in missing DNIS..." % (str(threading.current_thread().ident)))
            CallData['fldDNIS'] = str(config.get('TelSwitch', 'PARKNUMBER'))
        if not 'fldCSN' in CallData:
            logwrite.debug("%s: Phantom resume request received, attempting to match to current call..." % (str(threading.current_thread().ident)))
            callCheck = self.checkDuplicateCalls(str(CallData['agentID']))
            if callCheck[0] == True:
                logwrite.debug("%s: Current call matched! resuming recording..." % (str(threading.current_thread().ident)))
                return [True, "OK(" + callCheck[1] + ")\r\n"]
            else:
                logwrite.debug("%s: Couldn't find current call, not enough data to make new recording, returning error..." % (str(threading.current_thread().ident)))
                return [False, False]
        callsKilled = self.killDuplicateCalls(str(CallData['agentID']))
        if str(callsKilled) == "ERROR":
            return [False, False]
        # Now that we've cleaned up, let's start the recording
        # Check to see if folder for today exists, if not, create ite
        now = datetime.now()
        folder = str(config.get('FreeSWITCH', 'LOGGERDIR')) + "/" + str(now.strftime("%Y-%m-%d"))
        logwrite.debug("%s: Checking if folder %s exists..." % (str(threading.current_thread().ident), folder))
        if not os.path.isdir(folder):
            try:
                logwrite.debug("%s: Folder %s does not exist, creating..." % (str(threading.current_thread().ident), folder))
                os.makedirs(folder)
                # Change ownership to FreeSWITCH user so FreeSWITCH can write
                uid = pwd.getpwnam(str(config.get('FreeSWITCH', 'FSUID'))).pw_uid
                gid = grp.getgrnam(str(config.get('FreeSWITCH', 'FSGID'))).gr_gid
                os.chown(folder, uid, gid)
                logwrite.debug("%s: Folder %s created!" % (str(threading.current_thread().ident), folder))
            except(Exception) as e:
                logwrite.error("%s: Unable to create folder %s : %s" % (str(threading.current_thread().ident), folder, e))
                returnVar = [False, False]
                return returnVar
        else:
            uid = pwd.getpwnam(str(config.get('FreeSWITCH', 'FSUID'))).pw_uid
            gid = grp.getgrnam(str(config.get('FreeSWITCH', 'FSGID'))).gr_gid
            os.chown(folder, uid, gid)
        # Generate a filename
        recordname = str(now.strftime("%Y-%m-%d_%H%M%S_%f")) + '-' + str(CallData['fldCSN']) + '.' + str(config.get('FreeSWITCH', 'FILEEXT'))
        filename = folder + '/' + recordname
        logwrite.debug("%s: Filename to record: %s" % (str(threading.current_thread().ident), filename))
        # Generate our outbound gateways
        gatewayFinal = ''
        gatewayLimit = 0
        gateways = config.items('FreeSWITCH-Gateways')
        # Randomize gateway list to minimize chance of race condition
        random.shuffle(gateways)
        for key, gateway in gateways:
            gwData = json.loads(gateway)
            try:
                gwCheck = self.checkGateways(gwData[0], gwData[1])
            except (Exception) as e:
                logwrite.error("%s: Unable to check gateway : %s" % (str(threading.current_thread().ident), e))
                pass
            if gwCheck:
                gatewayFinal = str(gwData[0])
                gatewayLimit = int(gwData[1])
                break
        if gatewayFinal == '':
            #If we get here all gateways are at max capactity
            logwrite.error("%s: No gateways available to originate! Aborting..." % (str(threading.current_thread().ident)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger start failure for CSN: %s" % (str(CallData['fldCSN']))
                emailMessage = "All gateways are at maximum capacity, but unable to start recording for CSN: %s" % (str(CallData['fldCSN']))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            returnVar = [False, False]
            return returnVar
        origGateway = "sofia/gateway/" + str(gatewayFinal) + "/" + str(config.get('FreeSWITCH', 'DIALSTRING')) + str(CallData['agentID'])
        # Originate the call
        origString = "{gw_name=" + str(gatewayFinal) + ",max_calls=" + str(gatewayLimit) + ",agent_id=" + str(CallData['agentID']) + ",agent_login_id=" + str(CallData['fldAgentLoginID']) + ",call_dnis=" + str(CallData['fldDNIS']) + ",call_ani=" + str(CallData['fldANI']) + ",call_type=" + str(CallData['fldCallType']) + ",call_csn=" + str(CallData['fldCSN']) + ",call_acct=" + str(CallData['fldClientID']) + ",recording_file=" + filename + ",recording_paused=0,pausearr=ARRAY::START>>0}" + origGateway + " &lua(" + str(config.get('FreeSWITCH', 'FSLUA')) + ")"
        logwrite.debug("%s: Sending command to freeswitch: originate %s" % (str(threading.current_thread().ident), origString))
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(config.get('FreeSWITCH', 'FSHOST'), config.get('FreeSWITCH', 'FSPORT'), config.get('FreeSWITCH', 'FSPASSWORD'))
        if fscon.connected():  
            orig = fscon.api("originate", origString)
            OrigResult = orig.getBody().strip()
            status = OrigResult[:3]
            if status == "+OK":
                origUUID =  OrigResult[4:]
            else:
                logwrite.error("%s: Unable to originate call in FreeSWITCH, received error: %s. responding with ERROR" % (str(threading.current_thread().ident), OrigResult))
                if config.get('Notification', 'NOTIFICATION') == 'true':
                    emailSubject = "Logger start failure for CSN: %s" % (str(CallData['fldCSN']))
                    emailMessage = "Call originated, but unable to start recording for CSN: %s, received the following error: %s.\n\nCall Data:\n\n%s" % (str(CallData['fldCSN']), str(OrigResult), str(origString))
                    logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                    self.sendEmail(emailSubject, emailMessage)
                returnVar = [False, False]
                fscon.disconnect()
                return returnVar
            # Sleep for a tiny bit, then check if our call is still active. If not, the recording didn't start...
            time.sleep(.45)
            fsreturn = fscon.api("uuid_buglist", origUUID)
            UUIDAlive = fsreturn.getBody().strip()
            if UUIDAlive[:4] == "-ERR":
                logwrite.error("%s: Call originated, but unable to start recording in FreeSWITCH, received the following error: %s. Responding with ERROR" % (str(threading.current_thread().ident), UUIDAlive))
                if config.get('Notification', 'NOTIFICATION') == 'true':
                    emailSubject = "Logger start failure for CSN: %s" % (str(CallData['fldCSN']))
                    emailMessage = "Call originated, but unable to start recording for CSN: %s, received the following error: %s.\n\nCall Data:\n\n%s" % (str(CallData['fldCSN']), str(UUIDAlive), str(origString))
                    logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                    self.sendEmail(emailSubject, emailMessage)
                returnVar = [False, False]
                fscon.disconnect()
                return returnVar
        else:
            logwrite.error("%s: Unable to connect to FreeSWITCH to originate call, responding with ERROR" % (str(threading.current_thread().ident)))
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger start failure for CSN: %s" % (str(CallData['fldCSN']))
                emailMessage = "Unable to connect to FreeSWITCH to start recording for CSN: %s, received the following error: %s.\n\nCall Data:\n\n%s" % (str(CallData['fldCSN']), str(UUIDAlive), str(origString))
                logwrite.debug("%s: Sending alert email" % (str(threading.current_thread().ident)))
                self.sendEmail(emailSubject, emailMessage)
            returnVar = [False, False]
            return returnVar
        returnVar = [True, "OK(" + recordname + ")"]
        return returnVar

    def sendEmail(self, subj, mesg):
        """ Sends email
        
        Sends email to address(es) defined in config file
        Server parameters are also defined in config file
        
        Args:
            self: This class
            subj: Message subject
            mesg: Message content
        """
        tolist = str(config.get('Notification', 'TOEMAIL')).replace(", ",",").split(",")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subj
        msg['From'] = str(config.get('Notification', 'FROMEMAIL'))
        msg['To'] = str(config.get('Notification', 'TOEMAIL'))
        body = MIMEText(mesg, 'plain')
        msg.attach(body)
        server = smtplib.SMTP(str(config.get('Notification', 'SMTPSERVER')), str(config.get('Notification', 'SMTPPORT')))
        server.ehlo()
        if str(config.get('Notification', 'SMTPTLS')) == "true":
            try:
                server.starttls()
            except (Exception) as e:
                logwrite.error("%s: Unable to start TLS to send email, falling back to plain: %s" % (str(threading.current_thread().ident), str(e)))
        if str(config.get('Notification', 'SMTPAUTH')) == "true":
            try:
                server.login(str(config.get('Notification', 'SMTPUSER')), str(config.get('Notification', 'SMTPPASS')))
            except (Exception) as e:
                logwrite.error("%s: Unable to authenticate to email server: %s" % (str(threading.current_thread().ident), str(e)))
        server.set_debuglevel(0)
        try:
            server.sendmail(str(config.get('Notification', 'FROMEMAIL')), tolist, msg.as_string())
        except (Exception) as e:
            logwrite.error("%s: Unable to send alert email: %s" % (str(threading.current_thread().ident), str(e)))
        server.quit()
        return True
            

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(
            self, server_address, RequestHandlerClass)
        self._shutdown_request = False


try:
    # If we're already listening on port, kill the process
    logwrite.info("Starting up logger")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logwrite.info("Checking to see if port %s is already in use..." %
                  (str(config.get('Network', 'TCPPORT'))))
    result = sock.connect_ex(
        ('127.0.0.1', int(config.get('Network', 'TCPPORT'))))
    if result == 0:
        logwrite.error("Port %s is currently in use. Please ensure logger application is not already running. Exiting..." %
                       (str(config.get('Network', 'TCPPORT'))))
        sys.exit(2)
    else:
        logwrite.info("Port %s is available!" %
                      (str(config.get('Network', 'TCPPORT'))))
    # Set up threaded TCP server to serve forever, then start the thread
    logwrite.info("Starting listener service on port %s" %
                  (str(config.get('Network', 'TCPPORT'))))
    t = ThreadedTCPServer(
        ('', int(config.get('Network', 'TCPPORT'))), listenerService)
    server_thread = threading.Thread(target=t.serve_forever())
    server_thread.start()
# Exit catchall. Perform cleanup.
except(KeyboardInterrupt, SystemExit):
    logwrite.warning("Caught signal, cleaning up and shutting down...")
    try:
        logwrite.info("Shutting down all listener threads...")
        t.shutdown()
        t.server_close()
        logwrite.info("Listener threads terminated.")
    except:
        logwrite.error("No listener running, skipping thread shutdown.")
    if result != 0:
        sys.exit()
    else:
        logwrite.warning("Terminating program...")
        sys.exit()
