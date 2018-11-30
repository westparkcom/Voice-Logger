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
from logging.handlers import TimedRotatingFileHandler
import random
import ESL #pip3 install python-ESL
import psycopg2 #pip3 install psycopg2
try:
    import simplejson as json
except ImportError:
    import json
import pwd
import grp
import smtplib
import uuid
import wave
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def fsconnection():
    """
    Opens a new connection to the FreeSWITCH API
    Returns the connection

    Args:
        None
    """
    fsconx = ESL.ESLconnection(
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
    return fsconx

def dbquery(dbname, query):
    """
    Queries database using FreeSWITCH
    Returns the result object

    Args:
        dbname: Name of the database to be queried
        tablename: Name of the table to be queried
        query: string of the SQL query
    """
    try:
        conn = psycopg2.connect(
            "host={} dbname={} user={} password={}".format(
                config.get(
                    'ACD-Database',
                    'ACDDB-SERVER'
                ),
                dbname,
                config.get(
                    'ACD-Database',
                    'ACDDB-USER'
                ),
                config.get(
                    'ACD-Database',
                    'ACDDB-PASSWORD'
                ),
            )
        )
    except (Exception) as e:
        logwrite.error(
            "Unable to connect to database {}: {}".format(
                dbname,
                e
            )
        )
        return [
            False,
            []
        ]
    try:
        results = []
        cur = conn.cursor()
        cur.execute(query)
        columns = [column[0] for column in cur.description]
        for row in cur.fetchall():
            results.append(
                dict(
                    zip(
                        columns,
                        row
                    )
                )
            )
        conn.close()
        return [
            True,
            results
        ]
    except (Exception) as e:
        logwrite.error(
            "Unable to query database {}: {}".format(
                dbname,
                e
            )
        )
        return [
            False,
            []
        ]

def checkrecording(agentID):
    success, metadata = getcallmetadata(
        agentID
    )
    if 'Station' in metadata:
        return [
            success,
            True
        ]
    else:
        return [
            success,
            False
        ]

def getcallmetadata(agentID):
    fscon = fsconnection()
    if not fscon.connected():
        return [
            False,
            {}
        ]
    try:
        jsonfile = fscon.api(
            "db",
            "select/recordings/{}".format(
                agentID
            )
        ).getBody().strip()
        fscon.disconnect()
        with open(jsonfile) as jfile:
            metadata=json.load(jfile)
    except (Exception) as e:
        # json loads failed file doesn't exist
        return [
            False,
            {'error': e}
        ]
    return [
        True,
        metadata
    ]

def clearcallmetadata(agentID):
    success, metadata = getcallmetadata(agentID)
    fscon = fsconnection()
    if not fscon.connected():
        return False
    result = fscon.api(
        "db",
        "select/recordings/{}".format(
            agentID
        )
    ).getBody().strip()
    fscon.api(
        "db",
        "delete/recordings/{}".format(
            agentID
        )
    ).getBody().strip()
    fscon.disconnect()
    if result == '!err!':
        return False
    metadata['Completed'] = True
    return dropjsonfile(
        metadata,
        result
    )

def setcallmetadata(agentID, metadict):
    fscon = fsconnection()
    if not fscon.connected():
        return [
            False,
            'Unable to connect to FreeSWITCH'
        ]
    jsonfile = fscon.api(
        'db',
        'select/recordings/{}'.format(
            agentID,
        )
    ).getBody().strip()
    if os.path.exists(jsonfile):
        outfile = jsonfile
    else:
        success, outfile = filenamegen(
            False,
            metadict['CSN'],
            'json'
        )
    result = fscon.api(
        'db',
        'insert/recordings/{}/{}'.format(
            agentID,
            outfile
        )
    ).getBody().strip()
    fscon.disconnect()
    if result == '!err!': #TODO FIXME: ensure !err! is the appropriate error response
        return [
            False,
            result
        ]
    else:
        dropjsonfile(
            metadict,
            outfile
        )
        return [
            True,
            result
        ]

def checkvalidagent(agentID):
    # Query to see if agent is signed into the switch and has a UUID
    success, rows = dbquery(
        config.get(
            'ACD-Database',
            'ACDDB-DB'
        ),
        "SELECT * FROM agents WHERE agent = {}".format(
            int(
                agentID
            )
        )
    )
    # If we had a database problem, return False
    if not success:
        return [
            False,
            ''
        ]
    # If the agent ID isn't in the database, return False
    if len(rows) == 0:
        logwrite.warning(
            "{}: Agent ID {} not found in ACD database".format(
                threading.current_thread().ident,
                agentID
            )
        )
        return [
            False,
            ''
        ]
    agentinfo = rows[0]
    # If the agent isn't connected to the switch, return False
    if agentinfo['agent_uuid'] == '':
        logwrite.warning(
            "{}: Agent ID {} not currently connected to ACD switch".format(
                threading.current_thread().ident,
                agentID
            )
        )
        return [
            False,
            ''
        ]
    return [
        True,
        agentinfo['agent_uuid']
    ]

def checkrecordingpath(dateobj):
    folder = os.path.join(
        config.get(
            'FreeSWITCH',
            'LOGGERDIR'
        ),
        dateobj.strftime(
            "%Y-%m-%d"
        )
    )
    if not os.path.isdir(folder):
        try:
            logwrite.debug(
                "Folder {} does not exist, creating...".format(
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
                "Folder {} created!".format(
                    folder
                )
            )
            return [
                True,
                folder
            ]
        except(Exception) as e:
            logwrite.error(
                "Unable to create folder {} : {}".format(
                    folder,
                    e
                    )
                )
            return [
                False,
                ''
            ]
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
        return [
            True,
            folder
        ]


def filenamegen(usedate, CSN, fileext):
    now = datetime.now()
    if usedate:
        pathgood, path = checkrecordingpath(now)
        if not pathgood:
            return [
                False,
                ''
            ]
    else:
        path = config.get(
            'FreeSWITCH',
            'LOGGERDIR'
        )
    recordname = "{}-{}.{}".format(
        now.strftime("%Y-%m-%d_%H%M%S_%f"),
        CSN,
        fileext
    )
    return [
        True,
        os.path.join(
            path,
            recordname
        )
    ]

def dropjsonfile(jsonmeta, filename):
    now = datetime.now()
    jsonmeta['AccessTime'] = int(
        round(
            (
                now - datetime.strptime(
                    jsonmeta['LoggerDate'],
                    "%Y-%m-%d %H:%M:%S"
                )
            ).seconds
        )
    )
    try:
        with open(filename, 'w') as outfile:
            json.dump(
                jsonmeta,
                outfile,
                separators=(',', ':')
            )
        return True
    except (Exception) as e:
        logwrite.error(
            "Unable to write JSON file: {}".format(
                e
            )
        )
        return False


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
            logwrite.info(
                "{}: Client connected from address {}:{}".format(
                    threading.current_thread().ident,
                    self.client_address[0],
                    self.client_address[1]
                    )
                )
            data = 'dummy' # Needed to enter the while loop
            while len(data):
                self.request.settimeout(
                    int(
                        config.get(
                            'Network',
                            'TCPTIMEOUT'
                        )
                    )
                )
                data = self.request.recv(4096)
                logwrite.debug(
                    "{}: Received data: {}".format(
                        threading.current_thread().ident,
                        data.decode('utf-8')
                        )
                    )
                cleandata = data.decode('utf-8').strip()
                # Send what we received off to be processed
                response = bytes(
                    self.RequestHandler(cleandata),
                    'utf8'
                )
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
        what we should do with it. There are currently 6 menthods we are
        aware of that PInnacle client sends:
            START(agentID,fldClientID=XXXX,fldDNIS=XXXXXXXXXX,fldANI=XXXXXXXXXX,fldCallType=X,fldCSN=XXXXXXX,fldAgentLoginID=XXX)
            START(agentID)
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
        
        # Check if outer parenthesis exist
        if not ((CallParameters[0] == '(') or (CallParameters[-1] == ')')):
            return {'BADDATA': True}
        params = 'agentID={}'.format(
            CallParameters[1:-1]
            ).split(',')
        paramsDict = dict(
            param.split(
                '=',
                1
            ) for param in params
        )
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
        validagent, agentUUID = checkvalidagent(
            agentID
        )
        if not validagent:
            return [
                False,
                'NOT RECORDING'
            ]

        # If we've gotten past the basics we can see if there's actually recording info in FreeSWITCH
        reccheck, metadata = getcallmetadata(
            agentID
        )
        if not reccheck:
            logwrite.debug(
                "{}: No active recordings found for agent ID: {}".format(
                    threading.current_thread().ident,
                    agentID
                )
            )
            return [
                False,
                "NOT RECORDING"
            ]
        
        # All tests passed, now let's stop/start recordings, ensure paused is set to 1, and push metadata
        fscon = fsconnection()
        if not fscon.connected():
            logwrite.warning(
                "{}: Unable to connect to FreeSWITCH to {} recording for agent ID: {}".format(
                    threading.current_thread().ident,
                    action,
                    agentID
                )
            )
            return [
                False,
                "NOT RECORDING"
            ]
        if action == 'mask':
            fsresult = fscon.api(
                'uuid_record',
                '{} stop all'.format(
                    agentUUID
                )
            ).getBody().strip()
            logwrite.debug(
                "{}: Result for 'uuid_record {} stop all: {}'".format(
                    threading.current_thread().ident,
                    agentUUID,
                    fsresult
                )
            )
            fscon.disconnect()
            if fsresult[0:3] == '-ERR': #TODO FIXME get the appropriate return value for failure to stop recording
                logwrite.info(
                    "{}: No recordings to stop for agent ID: {}".format(
                        threading.current_thread().ident,
                        agentID
                    )
                )
                return [
                    False,
                    'NOT RECORDING'
                ]
            return [
                True,
                'OK'
            ]
        elif action == 'unmask':
            fnamesuccess, newfile = filenamegen(
                True,
                metadata['CSN'],
                'wav'
            )
            metadata['Recordings'].append(newfile)
            fsresult = fscon.api(
                'uuid_record',
                '{} start {}'.format(
                    agentUUID,
                    newfile
                )
            ).getBody().strip()
            logwrite.debug(
                "{}: Result for 'uuid_record {} start {}': {}".format(
                    threading.current_thread().ident,
                    agentUUID,
                    newfile,
                    fsresult
                )
            )
            fscon.disconnect()
            if fsresult[0:3] == '-ERR': #TODO FIXME get the appropriate return value for failure to stop recording
                logwrite.info(
                    "{}: Unable to start recording for agent ID {}: {}".format(
                        threading.current_thread().ident,
                        agentID,
                        fsresult
                    )
                )
                
                return [
                    False,
                    'NOT RECORDING'
                ]
            setresult, seterr = setcallmetadata(
                agentID,
                metadata
            )
            if not setresult:
                logwrite.warning(
                    "{}: Unable to store recording metadata for agent ID {}: {}".format(
                        threading.current_thread().ident,
                        agentID,
                        seterr
                    )
                )
                return [
                    False,
                    'INTERNAL ERROR'
                ]
            return [
                True,
                'OK'
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
        validagent, agentUUID = checkvalidagent(
            agentID
        )
        if not validagent:
            return [
                False,
                'NOT RECORDING'
            ]

        # If we've gotten past the basics we can see if there's actually recording info in FreeSWITCH
        reccheck, metadata = getcallmetadata(
            agentID
        )
        if not reccheck:
            logwrite.debug(
                "{}: No active recordings found for agent ID: {}".format(
                    threading.current_thread().ident,
                    agentID
                )
            )
            return [
                False,
                "NOT RECORDING"
            ]
        
        # All tests passed, now let's get all the metadata, stop recordings, and clear the recording metadata
        fscon = fsconnection()
        if not fscon.connected():
            logwrite.warning(
                "{}: Unable to connect to FreeSWITCH to stop recordings for agent ID: {}".format(
                    threading.current_thread().ident,
                    agentID
                )
            )
            return [
                False,
                "NOT RECORDING"
            ]
        fsresult = fscon.api(
            'uuid_record',
            '{} stop all'.format(
                agentUUID
            )
        ).getBody().strip()
        fscon.disconnect()
        logwrite.debug(
            "{}: Result for uuid_record {} stop all: {}".format(
                threading.current_thread().ident,
                agentUUID,
                fsresult
            )
        )
        if fsresult[0:3] == '-ERR': #TODO FIXME get the appropriate return value for failure to stop recording
            logwrite.info(
                "{}: No recordings to stop for agent ID: {}".format(
                    threading.current_thread().ident,
                    agentID
                )
            )
        metacleared = clearcallmetadata(agentID)
        if not metacleared:
            logwrite.warning(
                "{}: Unable to clear recordings metadata for agent ID: {}".format(
                    threading.current_thread().ident,
                    agentID
                )
            )
        return [
            True,
            "OK"
            ]

    
    def OriginateRecording(self, CallData):
        """ Starts recording call
        
        Sends command to FreeSWITCH to begin recording call. Checks
        to see if there is already an active recording for the agentID
        and stops if exists. 
        
        Args:
            self: This class
            CallData: (dict) The data received from PInnacle that has been parsed
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
                "{}: Phantom resume request received for agent ID {}, attempting to resume recording...".format(
                    threading.current_thread().ident,
                    CallData['agentID']
                    )
                )
            return self.PauseResumeRecording(
                CallData['agentID'],
                'unmask'
            )
        # run the stop procedure as a precaution
        stopresult, stopmsg = self.StopRecording(
            CallData['agentID']
        )
        if stopresult:
            logwrite.debug(
                "{}: Recordings existed for agent ID {}, cleaning up PInnacle's mess...".format(
                    threading.current_thread().ident,
                    CallData['agentID']
                )
            )
        checksuccess, agentUUID = checkvalidagent(
            CallData['agentID']
        )
        if not checksuccess:
            logwrite.warning(
                "{}: agent ID {} not logged in, aborting...".format(
                    threading.current_thread().ident,
                    CallData['agentID']
                )
            )
            return [
                False,
                'NOT RECORDING'
            ]
        fnamesuccess, recording_file = filenamegen(
            True,
            CallData['fldCSN'],
            'wav'
        )
        metadict = {
            'Station': CallData['agentID'],
            'ClientID': CallData['fldClientID'],
            'InboundFlag': CallData['fldCallType'],
            'DNIS': CallData['fldDNIS'],
            'ANI': CallData['fldANI'],
            'CSN': CallData['fldCSN'],
            'LoggerDate': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'UniqueID': str(uuid.uuid4()),
            'Paused': 0,
            'Recordings': [
                recording_file
            ],
            'Completed': False
        }
        setresult, seterr = setcallmetadata(
            CallData['agentID'],
            metadict
        )
        if not setresult:
            logwrite.warning(
                "{}: Unable to set metadata for agent ID {}! Cannot start recording. Error Info: {}".format(
                    threading.current_thread().ident,
                    CallData['agentID'],
                    seterr
                )
            )
            return [
                False,
                'INTERNAL ERROR'
            ]
        fscon = fsconnection()
        if not fscon.connected():
            logwrite.warning(
                "{}: Unable to connect to FreeSWITCH to stop recordings for agent ID: {}".format(
                    threading.current_thread().ident,
                    CallData['agentID']
                )
            )
            return [
                False,
                "NOT RECORDING"
            ]
        fsresult = fscon.api(
            'uuid_record',
            '{} start {}'.format(
                agentUUID,
                recording_file
            )
        ).getBody().strip()
        logwrite.debug(
            "{}: Result for 'uuid_record {} start {}': {}".format(
                threading.current_thread().ident,
                agentUUID,
                recording_file,
                fsresult
            )
        )
        fscon.disconnect()
        if fsresult == 'ERR': #TODO FIXME get the appropriate return value for failure to stop recording
            logwrite.info(
                "{}: Unable to start recording for agent ID {}: {}".format(
                    threading.current_thread().ident,
                    CallData['agentID'],
                    fsresult
                )
            )
            
            return [
                False,
                'NOT RECORDING'
            ]
        return [
            True,
            'OK({})'.format(
                os.path.split(
                    recording_file
                )[1]
            )
        ]

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
        loggerConfigFile = argsDict['--config']
    except:
        print("")
        print("Error: logger configuration file location not specified.")
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini".format(sys.argv[0]))
        sys.exit(1)
            
    # Global config
    config = ConfigParser.ConfigParser()
    config.read(
        loggerConfigFile
        )

    # Logging setup
    logwrite = logging.getLogger(
        "Rotating Log"
        )
    # Set the log level
    logwrite.setLevel ( config.get ( 'Logging', 'LOGLEVEL'))
    if config.get('Logging', 'LOGLEVEL') == 'DEBUG':
        logwrite.setLevel(
            logging.DEBUG
        )
    elif config.get('Logging', 'LOGLEVEL') == 'INFO':
        logwrite.setLevel(
            logging.INFO
        )
    elif config.get('Logging', 'LOGLEVEL') == 'WARNING':
        logwrite.setLevel(
            logging.WARNING
        )
    elif config.get('Logging', 'LOGLEVEL') == 'ERROR':
        logwrite.setLevel(
            logging.ERROR
        )
    elif config.get('Logging', 'LOGLEVEL') == 'CRITICAL':
        logwrite.setLevel(
            logging.CRITICAL
        )
    handler = TimedRotatingFileHandler(
        config.get(
            'Logging',
            'LOGLOCATION'
        ),
        when='{}'.format(
            config.get(
                'Logging',
                'ROTATEWHEN'
            )
        ),
        interval = int(
            config.get(
                'Logging',
                'ROTATEINTERVAL'
            )
        ),
        backupCount = int(
            config.get(
                'Logging',
                'ROTATEBACKUPCOUNT'
            )
        )
    )
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s:%(levelname)s: %(message)s'
        )
    )
    logwrite.addHandler(
        handler
    )
    # Call main program
    sys.exit(main())