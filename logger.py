#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
#################################################################
#                                                               #
# Copyright (c) 2018 Westpark Communications, L.P.              #
# Subject to the GNU Affero GPL license                         #
# See the file LICENSE.md for details                           #
#                                                               #
#################################################################
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer
import threading
from datetime import date, datetime
import time
import sys
import socket
import os
try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
import logging
import logging.config
import random
import ESL
try:
    import simplejson as json
except ImportError:
    import json
import pwd
import grp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
            logwrite.info(
                "{}: Client connected from address {}:{}".format(
                    threading.current_thread().ident,
                    self.client_address[0],
                    self.client_address[1]
                    )
                )
            while len(data):
                self.request.settimeout(int(config.get('Network', 'TCPTIMEOUT')))
                data = self.request.recv(4096)
                logwrite.debug(
                    "{}: Received data: {}".format(
                        threading.current_thread().ident,
                        data.decode('utf-8')
                        )
                    )
                cleandata = data.decode('utf-8').strip()
                # Send what we received off to be processed
                response = bytes(self.RequestHandler(cleandata))
                self.request.send(response)
            logwrite.info(
                "{}: Client {}:{} disconnected".format(
                    threading.current_thread().ident,
                    self.client_address[0],
                    self.client_address[1]
                    )
                )
            self.request.close()
            return
            
        except(
            socket.timeout,
            socket.error,
            threading.ThreadError,
            Exception
            ) as e:
            if "{}".format(e) == 'timed out':
                logwrite.info(
                    "{}: Connection {} for client {}:{}".format(
                        threading.current_thread().ident,
                        e,
                        self.client_address[0],
                        self.client_address[1]
                        )
                    )
            else:
                logwrite.exception(
                    "{}: Error:".format(
                        threading.current_thread(),
                        )
                    )
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
            logwrite.warning(
                "{}: Invalid command received: {}".format(
                    threading.current_thread().ident,
                    RequestData
                    )
                )
            respresult = "ERROR(NOT VALID COMMAND)\r\n"
            logwrite.debug(
                "{}: Responding with: {}".format(
                    threading.current_thread().ident,
                    respresult
                    )
                )
            return respresult
        if RequestData[0:5] == "START":
            callParams = self.Parse(
                RequestData[5:]
                )
            if 'BADDATA' in callParams:
                logwrite.warning(
                    "{}: Invalid command received: {}".format(
                        threading.current_thread().ident,
                        RequestData
                        )
                    )
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            originateResult = self.OriginateRecording(
                callParams
                )
            if originateResult[0] == False:
                respresult = "ERROR(NOT RECORDING)\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            elif originateResult[0] == True:
                respresult = "{}\r\n".format(originateResult[1])
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
        elif RequestData[0:4] == "STOP":
            callParams = self.Parse(
                RequestData[4:]
                )
            if 'BADDATA' in callParams:
                logwrite.warning(
                    "{}: Invalid command received: {}".format(
                        threading.current_thread().ident,
                        RequestData
                        )
                    )
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            recstop = self.StopRecording(
                callParams['agentID']
                )
            if recstop[0] == True:
                respresult = "OK\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            else:
                respresult = "ERROR({})\r\n".format(
                    recstop[1]
                    )
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
        elif RequestData[0:5] == "PAUSE":
            callParams = self.Parse(
                RequestData[5:]
                )
            if 'BADDATA' in callParams:
                logwrite.warning(
                    "{}: Invalid command received: {}".format(
                        threading.current_thread().ident,
                        RequestData
                        )
                    )
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            recpaused = self.PauseResumeRecording(
                callParams['agentID'],
                "mask"
                )
            if recpaused[0] == True:
                respresult = "OK\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            else:
                respresult = "ERROR({})\r\n".format(
                    recpaused[1]
                    )
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
        elif RequestData[0:6] == "RESUME":
            callParams = self.Parse(
                RequestData[6:]
                )
            if 'BADDATA' in callParams:
                logwrite.warning(
                    "{}: Invalid command received: {}".format(
                        threading.current_thread().ident,
                        RequestData
                        )
                    )
                respresult = "ERROR(NOT VALID COMMAND)\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            recresume = self.PauseResumeRecording(
                callParams['agentID'],
                "unmask"
                )
            if recresume[0] == True:
                respresult = "OK\r\n"
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
            else:
                respresult = "ERROR({})\r\n".format(recresume[1])
                logwrite.debug(
                    "{}: Responding with: {}".format(
                        threading.current_thread().ident,
                        respresult
                        )
                    )
                return respresult
        elif RequestData[0:5] == "HELLO":
            now = datetime.now()
            helloStr = "OK {} Calls: {}\r\n".format(
                now.strftime("%m/%d/%Y %I:%M:%S %p"),
                random.randint(0, 999999)
                )
            logwrite.debug(
                "{}: Responding with: {}".format(
                    threading.current_thread().ident,
                    helloStr
                    )
                )
            return helloStr
        else:
            logwrite.warning(
                "{}: Invalid command received: {}".format(
                    threading.current_thread().ident,
                    RequestData
                    )
                )
            respresult = "ERROR(NOT VALID COMMAND)\r\n"
            logwrite.debug(
                "{}: Responding with: {}".format(
                    threading.current_thread().ident,
                    respresult
                    )
                )
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
            return {'BADDATA': True}
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
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():
            calls = fscon.api(
                "show",
                "channels as json"
                )
            CurrentCalls = json.loads(
                calls.getBody()
                )
            j = 0
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug(
                        "{}: Checking UUID {} for agent ID {}...".format(
                            threading.current_thread().ident,
                            row['call_uuid'],
                            agentID
                            )
                        )
                    varstring = "{} agent_id".format(
                        row['call_uuid']
                        )
                    pausearrstring = "{} pausearr".format(
                        row['call_uuid']
                        )
                    startepochstring = "{} answered_time".format(
                        row['call_uuid']
                        )
                    fsreturn = fscon.api(
                        "uuid_getvar",
                        varstring
                        )
                    fsreturn2 = fscon.api(
                        "uuid_getvar",
                        pausearrstring
                        )
                    fsreturn3 = fscon.api(
                        "uuid_getvar",
                        startepochstring
                        )
                    retAgentID = fsreturn.getBody().strip()
                    retPauseArr = fsreturn2.getBody().strip()
                    retStartEpoch = fsreturn3.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn(
                            "{}: Call for agent ID {} found, {} recording for {}...".format(
                                threading.current_thread().ident,
                                agentID,
                                action,
                                row['call_uuid']
                                )
                            )
                        filestring = "{} recording_file".format(
                            row['call_uuid']
                            )
                        filereturn = fscon.api(
                            "uuid_getvar",
                            filestring
                            )
                        filename = filereturn.getBody().strip()
                        output = fscon.api(
                            "uuid_record",
                            "{} {} {}".format(
                                row['call_uuid'],
                                action,
                                filename
                                )
                            )
                        logwrite.debug(
                            "{}: FreeSWITCH output: {}".format(
                                threading.current_thread().ident,
                                output.getBody().strip()
                                )
                            )
                        pausestring = "{} recording_paused 1".format(
                            row['call_uuid']
                            )
                        fscon.api(
                            "uuid_setvar",
                            pausestring
                            )
                        logwrite.debug(
                            "{}: Current epoch time: {}".format(
                                threading.current_thread().ident,
                                time.time()
                                )
                            )
                        logwrite.debug(
                            "{}: Call start epoch time: {}".format(
                                threading.current_thread().ident,
                                str(retStartEpoch)[:10]
                                )
                            )
                        prtime = int(time.time()) - int(str(retStartEpoch)[:10])
                        if action == "mask":
                            prechar = "PAUSE>>"
                        else:
                            prechar = "START>>"
                        pausetimes =  "{}|:{}{}".format(
                            retPauseArr,
                            prechar,
                            prtime
                            )
                        pausetimestr = "{} pausearr {}".format(
                            row['call_uuid'],
                            pausetimes
                        )
                        fscon.api(
                            "uuid_setvar",
                            pausetimestr
                            )
                        j += 1
                        time.sleep(.33)
            except (Exception) as e:
                if "{}".format(e) == "'rows'":
                    logwrite.debug(
                        "{}: No active recordings found for agent ID: {}".format(
                            threading.current_thread().ident,
                            agentID
                            )
                        )
                else:
                    logwrite.exception(
                        "{}: Unhandled Exception encountered:".format(
                            threading.current_thread().ident,
                            )
                        )
                fscon.disconnect()
                return [
                    False,
                    "NOT RECORDING"
                    ]
            fscon.disconnect()
            if j == 0:
                return [
                    False,
                    "NOT RECORDING"
                    ]
            else:
                return [
                    True,
                    "OK"
                    ]
        else:
            logwrite.error(
                "{}: Unable to connect to FreeSWITCH to {} call, responding with ERROR".format(
                    threading.current_thread().ident,
                    action
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger {} failure for agent ID: {}".format(
                    action,
                    agentID
                    )
                emailMessage = "Unable to connect to FreeSWITCH to {} recording for agent ID: {}.".format(
                    action,
                    agentID
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
            return [
                False,
                "INTERNAL ERROR"
                ]
    
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
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():
            calls = fscon.api(
                "show",
                "channels as json"
                )
            CurrentCalls = json.loads(
                calls.getBody()
                )
            j = 0
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug(
                        "{}: Checking UUID {} for agent ID {}...".format(
                            threading.current_thread().ident,
                            row['call_uuid'],
                            agentID
                            )
                        )
                    varstring = "{} agent_id".format(
                        row['call_uuid']
                    )
                    fsreturn = fscon.api(
                        "uuid_getvar",
                        varstring
                        )
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn(
                            "{}: Call for agent ID {} found, killing UUID {}...".format(
                                threading.current_thread().ident,
                                agentID,
                                row['call_uuid']
                                )
                            )
                        fscon.api(
                            "uuid_kill",
                            "{}".format(
                                row['call_uuid']
                                )
                            )
                        j += 1
                        time.sleep(.33)
            except (Exception) as e:
                if "{}".format(e) == "'rows'":
                    logwrite.debug(
                        "{}: No active recordings found for agent ID: {}".format(
                            threading.current_thread().ident,
                            agentID
                            )
                        )
                else:
                    logwrite.error(
                        "{}: Unhandled Exception encountered: {}".format(
                            threading.current_thread().ident,
                            e
                            )
                        )
                fscon.disconnect()
                return [False, "NOT RECORDING"]
            fscon.disconnect()
            if j == 0:
                return [False, "NOT RECORDING"]
            else:
                return [True, "OK"]
        else:
            logwrite.error(
                "{}: Unable to connect to FreeSWITCH to stop call, responding with ERROR".format(
                    threading.current_thread().ident
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger stop failure for agent ID: {}".format(
                    agentID
                    )
                emailMessage = "Unable to connect to FreeSWITCH to stop recording for agent: {}".format(
                    agentID
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
            return [
                False,
                "INTERNAL ERROR"
                ]
    
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
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api(
                "show",
                "channels as json"
                )
            CurrentCalls = json.loads(
                calls.getBody()
                )
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug(
                        "{}: Checking UUID {} for agent ID {}...".format(
                            threading.current_thread().ident,
                            row['call_uuid'],
                            agentID
                            )
                        )
                    varstring = "{} agent_id".format(row['call_uuid'])
                    fsreturn = fscon.api(
                        "uuid_getvar",
                        varstring
                        )
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.warn(
                            "{}: Duplicate call for agent ID {} found: {}...".format(
                                threading.current_thread().ident,
                                agentID,
                                row['call_uuid']
                                )
                            )
                        filevarstring = "{} recording_file".format(
                            row['call_uuid']
                            )
                        fsreturn = fscon.api(
                            "uuid_getvar",
                            filevarstring
                            )
                        retFile = fsreturn.getBody().strip()
                        filenamestr = retFile.rsplit('/')[-1]
                        fscon.disconnect()
                        return [
                            True,
                            filenamestr
                            ]
            except (Exception) as e:
                if "{}".format(e) == "'rows'":
                    logwrite.debug(
                        "{}: No active recordings found for agent ID: {}".format(
                            threading.current_thread().ident,
                            agentID
                            )
                        )
                else:
                    logwrite.exception(
                        "{}: Unhandled Exception encountered:".format(
                            threading.current_thread().ident
                            )
                        )
                fscon.disconnect()
                return [
                    False,
                    False
                    ]
        else:
            logwrite.error(
                "{}: Unable to connect to FreeSWITCH to check duplicate calls, responding with ERROR".format(
                    threading.current_thread().ident
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger duplicate call check failure for agent ID: {}".format(
                    agentID
                    )
                emailMessage = "Unable to connect to FreeSWITCH to check for duplicate recordings for agent: {}".format(
                    agentID
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
            return [
                False,
                False
                ]
            
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
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api(
                "show",
                "channels as json"
                )
            CurrentCalls = json.loads(
                calls.getBody()
                )
            try:
                for row in CurrentCalls['rows']:
                    logwrite.debug(
                        "{}: Checking UUID {} for agent ID {}...".format(
                            threading.current_thread().ident,
                            row['call_uuid'],
                            agentID
                            )
                        )
                    varstring = "{} agent_id".format(
                        row['call_uuid']
                        )
                    fsreturn = fscon.api(
                        "uuid_getvar",
                        varstring
                        )
                    retAgentID = fsreturn.getBody().strip()
                    if str(retAgentID) == str(agentID):
                        logwrite.debug(
                            "{}: Duplicate call for agent ID {} found, killing UUID {}...".format(
                                threading.current_thread().ident,
                                agentID,
                                row['call_uuid']
                                )
                            )
                        fscon.api(
                            "uuid_kill", 
                            "{}".format(
                                row['call_uuid']
                                )
                            )
                        time.sleep(.33)
            except (Exception) as e:
                if "{}".format(e) == "'rows'":
                    logwrite.debug(
                        "{}: No calls found...".format(
                            threading.current_thread().ident
                            )
                        )
                    fscon.disconnect()
                    return False
                logwrite.debug(
                    "{}: Unhandled Exception encountered:, {}...".format(
                        threading.current_thread().ident,
                        e
                        )
                    )
                fscon.disconnect()
                return False
            fscon.disconnect()
            return True
        else:
            logwrite.error(
                "{}: Unable to connect to FreeSWITCH to kill call, responding with ERROR".format(
                    threading.current_thread().ident
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger recording kill failure for agent ID: {}".format(
                    agentID
                    )
                emailMessage = "Unable to connect to FreeSWITCH to kill duplicate recording for agent: {}".format(
                    agentID
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
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
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():
            # Let's check to see if we're already recording for this agent ID.
            # If we are, kill the call.
            calls = fscon.api(
                "limit_usage",
                "hash logger gw_{}".format(
                    gatewayName
                    )
                )
            currentCalls = calls.getBody()
            fscon.disconnect()
            if int(currentCalls) < int(maxCalls):
                logwrite.debug(
                    "{}: Gateway {} is currently at {} which is under MAXCALLS threshold of {}, using this gateway".format(
                        threading.current_thread().ident,
                        gatewayName,
                        currentCalls,
                        maxCalls
                        )
                    )
                return True
            else:
                logwrite.debug(
                    "{}: Gateway {} is currently at {} which is over MAXCALLS threshold of {}, skipping this gateway".format(
                        threading.current_thread().ident,
                        gatewayName,
                        currentCalls,
                        maxCalls
                        )
                    )
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
            logwrite.debug(
                "{}: Park resume request received, filling in missing DNIS...".format(
                    threading.current_thread().ident
                    )
                )
            CallData['fldDNIS'] = "{}".format(
                config.get(
                    'TelSwitch',
                    'PARKNUMBER'
                    )
                )
        if not 'fldCSN' in CallData:
            logwrite.debug(
                "{}: Phantom resume request received for agent ID {}, attempting to match to current call...".format(
                    threading.current_thread().ident,
                    CallData['agentID']
                    )
                )
            callCheck = self.checkDuplicateCalls(
                "{}".format(
                    CallData['agentID']
                    )
                )
            if callCheck[0] is None:
                if callCheck[0] == True:
                    logwrite.debug(
                        "{}: Current call matched for agent ID {}! resuming recording...".format(
                            threading.current_thread().ident,
                            CallData['agentID']
                            )
                        )
                    return [
                        True, 
                        "OK({})\r\n".format(
                            callCheck[1]
                            )
                        ]
            else:
                logwrite.debug(
                    "{}: Couldn't find current call for agent ID {}, not enough data to make new recording, returning error...".format(
                        threading.current_thread().ident,
                        CallData['agentID']
                        )
                    )
                return [
                    False,
                    False
                    ]
        callsKilled = self.killDuplicateCalls(
            "{}".format(
                CallData['agentID']
                )
            )
        if "{}".format(callsKilled) == "ERROR":
            return [
                False,
                False
                ]
        # Now that we've cleaned up, let's start the recording
        # Check to see if folder for today exists, if not, create ite
        now = datetime.now()
        folder = os.path.join(config.get('FreeSWITCH', 'LOGGERDIR'), now.strftime("%Y-%m-%d"))
        logwrite.debug(
            "{}: Checking if folder {} exists...".format(
                threading.current_thread().ident,
                folder
                )
            )
        if not os.path.isdir(folder):
            try:
                logwrite.debug(
                    "{}: Folder {} does not exist, creating...".format(
                        threading.current_thread().ident,
                        folder
                        )
                    )
                os.makedirs(folder)
                # Change ownership to FreeSWITCH user so FreeSWITCH can write
                uid = pwd.getpwnam(
                    config.get(
                        'FreeSWITCH',
                        'FSUID'
                        )
                    ).pw_uid
                gid = grp.getgrnam(
                    config.get(
                        'FreeSWITCH',
                        'FSGID'
                        )
                    ).gr_gid
                os.chown(
                    folder,
                    uid,
                    gid
                    )
                logwrite.debug(
                    "{}: Folder {} created!".format(
                        threading.current_thread().ident,
                        folder
                        )
                    )
            except(Exception) as e:
                logwrite.error(
                    "{}: Unable to create folder {} : {}".format(
                        threading.current_thread().ident,
                        folder,
                        e
                        )
                    )
                returnVar = [
                    False,
                    False
                    ]
                return returnVar
        else:
            uid = pwd.getpwnam(
                config.get(
                    'FreeSWITCH',
                    'FSUID'
                    )
                ).pw_uid
            gid = grp.getgrnam(
                config.get(
                    'FreeSWITCH',
                    'FSGID'
                    )
                ).gr_gid
            os.chown(
                folder,
                uid,
                gid
                )
        # Generate a filename
        recordname = "{}-{}.{}".format(
            now.strftime("%Y-%m-%d_%H%M%S_%f"),
            CallData['fldCSN'],
            config.get(
                'FreeSWITCH',
                'FILEEXT'
                )
            )
        filename = os.path.join(
            folder,
            recordname
            )
        logwrite.debug(
            "{}: Filename to record: {}".format(
                threading.current_thread().ident,
                filename
                )
            )
        # Generate our outbound gateways
        gatewayFinal = ''
        gatewayLimit = 0
        gateways = config.items(
            'FreeSWITCH-Gateways'
            )
        # Randomize gateway list to minimize chance of race condition
        random.shuffle(
            gateways
            )
        for key, gateway in gateways:
            gwData = json.loads(
                gateway
                )
            try:
                gwCheck = self.checkGateways(
                    gwData[0],
                    gwData[1]
                    )
            except (Exception) as e:
                logwrite.error(
                    "{}: Unable to check gateway : {}".format(
                        threading.current_thread().ident,
                        e
                        )
                    )
                pass
            if gwCheck:
                gatewayFinal = "{}".format(gwData[0])
                gatewayLimit = int(gwData[1])
                break
        if gatewayFinal == '':
            #If we get here all gateways are at max capactity
            logwrite.error(
                "{}: No gateways available to originate! Aborting...".format(
                    threading.current_thread().ident
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger start failure for CSN: {}".format(
                    CallData['fldCSN']
                    )
                emailMessage = "All gateways are at maximum capacity, but unable to start recording for CSN: {}".format(
                    CallData['fldCSN']
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
            returnVar = [
                False,
                False
                ]
            return returnVar
        origGateway = "sofia/gateway/{}/{}{}".format(
            gatewayFinal,
            config.get(
                'FreeSWITCH',
                'DIALSTRING'
                ),
            CallData['agentID']
            )
        # Originate the call
        origString = "{{gw_name={},max_calls={},agent_id={},agent_login_id={},call_dnis={},call_ani={},call_type={},call_csn={},call_acct={},recording_file={},recording_paused=0,pausearr=ARRAY::START>>0}}{} &lua({})".format(
            gatewayFinal,
            gatewayLimit,
            CallData['agentID'],
            CallData['fldAgentLoginID'],
            CallData['fldDNIS'],
            CallData['fldANI'],
            CallData['fldCallType'],
            CallData['fldCSN'],
            CallData['fldClientID'],
            filename,
            origGateway,
            config.get(
                'FreeSWITCH',
                'FSLUA'
                )
            )
        logwrite.debug(
            "{}: Sending command to freeswitch: originate {}".format(
                threading.current_thread().ident,
                origString
                )
            )
        # Connect to FreeSWITCH
        fscon = ESL.ESLconnection(
            config.get(
                'FreeSWITCH',
                'FSHOST'
                ),
            config.get(
                'FreeSWITCH',
                'FSPORT'
                ),
            config.get(
                'FreeSWITCH',
                'FSPASSWORD'
                )
            )
        if fscon.connected():  
            orig = fscon.api(
                "originate",
                origString
                )
            OrigResult = orig.getBody().strip()
            status = OrigResult[:3]
            if status == "+OK":
                origUUID =  OrigResult[4:]
            else:
                logwrite.error(
                    "{}: Unable to originate call in FreeSWITCH, received error: {}. responding with ERROR".format(
                        threading.current_thread().ident,
                        OrigResult
                        )
                    )
                if config.get('Notification', 'NOTIFICATION') == 'true':
                    emailSubject = "Logger start failure for CSN: {}".format(
                        CallData['fldCSN']
                        )
                    emailMessage = "Call originated, but unable to start recording for CSN: {}, received the following error: {}.\n\nCall Data:\n\n{}".format(
                        CallData['fldCSN'],
                        OrigResult,
                        origString
                        )
                    logwrite.debug(
                        "{}: Sending alert email".format(
                            threading.current_thread().ident
                            )
                        )
                    self.sendEmail(
                        emailSubject,
                        emailMessage
                        )
                returnVar = [
                    False,
                    False
                    ]
                fscon.disconnect()
                return returnVar
            # Sleep for a tiny bit, then check if our call is still active. If not, the recording didn't start, most likely because the caller disconnected...
            time.sleep(.45)
            fsreturn = fscon.api(
                "uuid_buglist",
                origUUID
                )
            UUIDAlive = fsreturn.getBody().strip()
            if UUIDAlive[:4] == "-ERR":
                logwrite.error(
                    "{}: Call originated, but unable to start recording in FreeSWITCH, received the following error: {}. Responding with ERROR".format(
                        threading.current_thread().ident,
                        UUIDAlive
                        )
                    )
                if config.get('Notification', 'NOTIFICATION') == 'true':
                    emailSubject = "Logger start failure for CSN: {}".format(
                        CallData['fldCSN']
                        )
                    emailMessage = "Call originated, but unable to start recording for CSN: {}, received the following error: {}.\n\nCall Data:\n\n{}".format(
                        CallData['fldCSN'],
                        UUIDAlive,
                        origString
                        )
                    logwrite.debug(
                        "{}: Sending alert email".format(
                            threading.current_thread().ident
                            )
                        )
                    self.sendEmail(
                        emailSubject,
                        emailMessage
                        )
                returnVar = [
                    False,
                    False
                    ]
                fscon.disconnect()
                return returnVar
        else:
            logwrite.error(
                "{}: Unable to connect to FreeSWITCH to originate call, responding with ERROR".format(
                    threading.current_thread().ident
                    )
                )
            if config.get('Notification', 'NOTIFICATION') == 'true':
                emailSubject = "Logger start failure for CSN: {}".format(
                    CallData['fldCSN']
                    )
                emailMessage = "Unable to connect to FreeSWITCH to start recording for CSN: {}, received the following error: {}.\n\nCall Data:\n\n{}".format(
                    CallData['fldCSN'],
                    UUIDAlive,
                    origString
                    )
                logwrite.debug(
                    "{}: Sending alert email".format(
                        threading.current_thread().ident
                        )
                    )
                self.sendEmail(
                    emailSubject,
                    emailMessage
                    )
            returnVar = [
                False,
                False
                ]
            return returnVar
        returnVar = [
            True,
            "OK({})".format(
                recordname
                )
            ]
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
        tolist = "{}".format(
            config.get(
                'Notification',
                'TOEMAIL'
                ).replace(
                    ", ",
                    ","
                    )
            ).split(
                ","
                )
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subj
        msg['From'] = "{}".format(
            config.get(
                'Notification',
                'FROMEMAIL'
                )
            )
        msg['To'] = "{}".format(
            config.get(
                'Notification',
                'TOEMAIL'
                )
            )
        body = MIMEText(mesg, 'plain')
        msg.attach(body)
        server = smtplib.SMTP(
            config.get(
                'Notification',
                'SMTPSERVER'
                ), 
            "{}".format(
                config.get(
                    'Notification',
                    'SMTPPORT'
                    )
                )
            )
        server.ehlo()
        if "{}".format(config.get('Notification', 'SMTPTLS')) == "true":
            try:
                server.starttls()
            except (Exception) as e:
                logwrite.error(
                    "{}: Unable to start TLS to send email, falling back to plain: {}".format(
                        threading.current_thread().ident,
                        e
                        )
                    )
        if "{}".format(config.get('Notification', 'SMTPAUTH')) == "true":
            try:
                server.login(
                    config.get(
                        'Notification',
                        'SMTPUSER'
                        ),
                    config.get(
                        'Notification',
                        'SMTPPASS'
                        )
                    )
            except (Exception) as e:
                logwrite.error(
                    "{}: Unable to authenticate to email server: {}".format(
                        threading.current_thread().ident,
                        e
                        )
                    )
        server.set_debuglevel(0)
        try:
            server.sendmail(
                config.get(
                    'Notification',
                    'FROMEMAIL'
                    ),
                tolist,
                msg.as_string()
                )
        except (Exception) as e:
            logwrite.error(
                "{}: Unable to send alert email: {}".format(
                    threading.current_thread().ident,
                    e
                    )
                )
        server.quit()
        return True
            

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(
            self, server_address, RequestHandlerClass)
        self._shutdown_request = False

def main():
    try:
        # If we're already listening on port, kill the process
        logwrite.info(
            "Starting up logger"
            )
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logwrite.info(
            "Checking to see if port {} is already in use...".format(
                config.get(
                    'Network',
                    'TCPPORT'
                    )
                )
            )
        result = sock.connect_ex(
            (
                '127.0.0.1',
                int(
                    config.get(
                        'Network',
                        'TCPPORT'
                        )
                    )
                )
            )
        if result == 0:
            logwrite.error(
                "Port {} is currently in use. Please ensure logger application is not already running. Exiting...".format(
                    config.get(
                        'Network',
                        'TCPPORT'
                        )
                    )
                )
            return 2
        else:
            logwrite.info(
                "Port {} is available!".format(
                    config.get(
                        'Network',
                        'TCPPORT'
                        )
                    )
                )
        # Set up threaded TCP server to serve forever, then start the thread
        logwrite.info(
            "Starting listener service on port {}".format(
                config.get(
                    'Network',
                    'TCPPORT'
                    )
                )
            )
        t = ThreadedTCPServer(
            (
                '',
                int(
                    config.get(
                        'Network',
                        'TCPPORT'
                        )
                    )
                ),
            listenerService
            )
        server_thread = threading.Thread(
            target=t.serve_forever()
            )
        server_thread.start()
    # Exit catchall. Perform cleanup.
    except(KeyboardInterrupt, SystemExit):
        logwrite.warning(
            "Caught signal, cleaning up and shutting down..."
            )
        try:
            logwrite.info(
                "Shutting down all listener threads..."
                )
            t.shutdown()
            t.server_close()
            logwrite.info(
                "Listener threads terminated."
                )
        except:
            logwrite.error(
                "No listener running, skipping thread shutdown."
                )
        if result != 0:
            return 1
        else:
            logwrite.warning("Terminating program...")
            return 0

if __name__ == "__main__":
    # Get config and logging info from CLI args
    i = 0
    argsDict = {}
    for item in sys.argv:
        if i == 0:
            i += 1
            pass
        else:
            i += 1
            paramname, paramval = item.partition("=")[::2]
            argsDict[paramname] = paramval

    try:
        loggerLogConfigFile = argsDict['--logconfig']
    except:
        print("")
        print("Error: log configuration file location not specified.")
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini --logconfig=/path/to/logconfigfile/loggerlog.ini".format(sys.argv[0]))
        sys.exit(1)
    try:
        loggerConfigFile = argsDict['--config']
    except:
        print("")
        print("Error: log configuration file location not specified.")
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini --logconfig=/path/to/logconfigfile/loggerlog.ini".format(sys.argv[0]))
        sys.exit(1)
            
    # Global config
    config = ConfigParser.ConfigParser()
    config.read(
        loggerConfigFile
        )

    # Logging setup
    logging.config.fileConfig(
        loggerLogConfigFile
        )
    logwrite = logging.getLogger(
        'loggerLog'
        )
    # Call main program
    sys.exit(main())