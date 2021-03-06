#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
#################################################################
#                                                               #
# Copyright (c) 2018 Westpark Communications, L.P.              #
# Subject to the GNU Affero GPL license                         #
# See the file LICENSE.md for details                           #
#                                                               #
# Purpose: Migrate Existing Logger to WPC-Logger                #
#                                                               #
# NOTE: Files migrated from WMA will have larger                #
#       filesizes. This is because MP3 at low bitrates          #
#       (8k) results in serious audio quality problems.         #
#       this scripts migrates all files to                      #
#       MP3 (mono, 8kHz, 16kbit). This uses approximately       #
#       1.5X - 3X the space as WMA. The benefit is device       #
#       compatibility                                           #
#                                                               #
# NOTE: In order to speed the migration up it is recommended to #
#       run this script for a 1 month interval, with several    #
#       instances of the script running simultaneously for      #
#       many different months - one instance per core optimal   #
#                                                               #
# NOTE: THIS MIGRATION TOOL IS EXPERIMENTAL AND MAY NOT WORK    #
#       IT HAS ALSO NOT BEEN TESTED AFTER PYTHON 3 REFACTOR     #
#                                                               #
# Usage: logger-migrate.py --start=YYYY/MM/DD --end=YYYY/MM/DD  #
#                                                               #
# Process: All records for the date range specified will be     #
#          loaded into memory. Script will iterate over each    #
#          record, locate the file for that record, convert     #
#          file from WMA to MP3 one at a time. The file         #
#          locations stored in the database are converted and   #
#          stored in an array which is dumped to file           #
#          (see Output).                                        #
#                                                               #
# Output:  cdr_csv file will be generated for the cron job to   #
#          consume. The entries are loaded into the database    #
#          PLEASE NOTE YOU SHOULD TURN OFF CRON DURING THIS     #
#          PERIOD AND RUN THE CRON SCRIPT MANUALLY AFTER EACH   #
#          INDIVIDUAL MIGRATION INSTANCE HAS COMPLETED!         #
#################################################################

# Microsoft SQL server on old logger server
dbserver = "10.10.10.10"
# Microsoft SQL server username
dbusername = "cmdata"
# Microsoft SQL server password
dbpassword = "password"
# Microsoft SQL server database to use
dbdatabase = "Subscriber"

# Source of the location where you mounted Logger directory
sourceloc = "/mnt/oldlogger/UMPlatform/Logger"
# Where the files are being migrated to
destloc = "/usr/share/freeswitch/sounds/logger"
# Location of cdr_csv files to be consumed by cron
cdrloc = "/var/log/freeswitch/cdr-csv"
# EXACT String from old logger database to separate the filename from the rest of the path
stripstring = "logger\\"

# Email notification when complete?
mailnotify = True
# Who will the email appear to come from
notifyfrom = "Tech <tech@yourdomain.com>"
# Who to send the email to
notifyto = ["Tech <tech@yourdomain.com>"]
# What SMTP server to use
smtpserver = "10.10.10.10"
# SMTP port
smtpport = 25
# SMTP Use TLS
smtptls = False
# Should we authenticate to the SMTP server
smtpauth = False
# STMP username
smtpuser = 'user'
# SMTP password
smtppass = 'pass'

# Whether to set permissions on files after conversion (not needed if writing to Windows share)
setpermissions = False
# FreeSWITCH UID for setting file permissions
fsuid = "freeswitch"
# FreeSWITCH GID for setting file permissions
fsgid = "freeswitch"

##############################################################

import pymssql
import uuid
import os
import sys
import smtplib
import pwd
import grp
import datetime
from subprocess import Popen, PIPE
from tqdm import tqdm
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    startday = argsDict['--start']
    datetime.datetime.strptime(startday, '%Y/%m/%d')
except:
    print("")
    print("Error: start date not specified or incorrect format.")
    print("")
    print("Usage: python {} --start=2016/01/01 --end=2016/01/31".format(sys.argv[0]))
    sys.exit(1)
try:
    endday = argsDict['--end']
    datetime.datetime.strptime(endday, '%Y/%m/%d')
except:
    print("")
    print("Error: end date not specified or incorrect format.")
    print("")
    print("Usage: python {} --start=2016/01/01 --end=2016/01/31".format(sys.argv[0]))
    sys.exit(1)
    
notifysubj = "Migration complete for dates {} to {}".format(
    startday,
    endday
    )


try:
    cdrfilename = os.path.join(
        cdrloc,
        "Master.csv.{}".format(
            uuid.uuid4()
            )
        )
    nofilename = os.path.join(
        cdrloc,
        "NoFile.csv.{}".format(
            uuid.uuid4()
            )
        )
    errorfilename = os.path.join(
        cdrloc,
        "Errors.log.{}".format(
            uuid.uuid4()
            )
        )
    f = open(
        cdrfilename,
        'w'
        )
    nf = open(
        nofilename,
        'w'
        )
    ef = open(
        errorfilename,
        'w'
        )

except (Exception) as e:
    print("Can't open file, error: {}".format(e))
    sys.exit(1)

con = pymssql.connect(
    dbserver,
    dbusername,
    dbpassword,
    dbdatabase
    )
cur = con.cursor()
cur.execute(
    "SELECT * FROM [CallLoggerStats] WHERE [LoggerDate] between '{} 00:00:00' and '{} 23:59:59'".format(
        startday,
        endday
        )
    )
rows = cur.fetchall()
dirsdict = {}
successful = 0
unsuccessful = 0
for row in tqdm(rows):
    fileloc = row[8].split(
        stripstring,
        1
        )[1]
    convertloc = os.path.join(
        sourceloc,
        fileloc.replace(
            "\\",
            "/"
            )
        )
    fileloc = fileloc[:-3] + "mp3"
    dircheckloc = os.path.join(
        destloc,
        fileloc.split(
            "\\",
            1
            )[0]
        )
    if not dircheckloc in dirsdict:
        dirsdict[dircheckloc] = dircheckloc
    if not os.path.isdir(dircheckloc):
        try:
            print("Creating directory {}".format(dircheckloc))
            os.makedirs(dircheckloc)
        except (Exception) as e:
            print("Error: {}".format(e))
            sys.exit(1)
    fileloc = os.path.join(
        destloc,
        fileloc.replace(
            "\\",
            "/"
            )
        )
    if not os.path.isfile(fileloc):
        ffcommand = [
            '/usr/local/bin/ffmpeg',
            '-hide_banner',
            '-loglevel',
            'error',
            '-i',
            convertloc,
            '-b:a',
            '16k',
            fileloc
            ]
        child = Popen(
            ffcommand,
            stdout=PIPE,
            stderr=PIPE
            )
        stdout, stderr = child.communicate()
        rc = child.returncode
        if rc == 0:
            f.write(
                "(Station,ClientID,InboundFlag,DNIS,ANI,CSN,AgentLoginID,AudioFilePath,LoggerDate,AccessTime,UniqueID,Paused) VALUES ({}, '{}','{}, '{}', {}, '{}', '{}', '{}', '{}', {}, '{}', 0);\n".format(
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    fileloc,
                    row[0],
                    row[10],
                    uuid.uuid4()
                    )
                )

            successful = successful + 1
        else:
            print(
                "Something went wrong converting file {} to {}:\n{}".format(
                    convertloc,
                    fileloc,
                    stderr
                    )
                )
            ef.write(
                "Error converting file {}: {}".format(
                    convertloc,
                    stderr
                    )
                )
            sqlout = "(Station,ClientID,InboundFlag,DNIS,ANI,CSN,AgentLoginID,AudioFilePath,LoggerDate,AccessTime,UniqueID,Paused) VALUES ({}, '{}','{}, '{}', {}, '{}', '{}', '{}', '{}', {}, '{}', 0);\n".format(
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    fileloc,
                    row[0],
                    row[10],
                    uuid.uuid4()
                    )
            print(
                "Here's the SQL so you can add it manually later if needed:\n{}".format(
                    sqlout
                    )
                )
            nf.write(
                "{}\n".format(
                    sqlout
                    )
                )
            unsuccessful = unsuccessful + 1
    row = cur.fetchone()
f.close()
ef.close()
nf.close()
con.close()

try:
    uid = pwd.getpwnam(
        fsuid
        ).pw_uid
except:
    print(
        "Warning: User {} not found. Skipping setting permissions".format(
            fsuid
            )
        )
    setpermissions = False
try:
    gid = grp.getgrnam(
        fsgid
        ).gr_gid
except:
    print(
        "Warning: Group {} not found. Skipping setting permissions".format(
            fsgid
            )
        )
    setpermissions = False

if setpermissions == True:
    for key, value in dirsdict.items():
        for root, dirs, files in os.walk(value):
            for direc in dirs:
                os.chown(
                    direc,
                    uid,
                    gid
                    )
            for file in files:
                fname = os.path.join(
                    root,
                    file
                    )
                os.chown(
                    fname,
                    uid,
                    gid
                    )
totalrecs = unsuccessful + successful 

notifymesg = """Old Logger Migration complete for dates: {} to {}
Total records: {}

Successful conversions: {}
Unseccessful conversions: {}""".format(
    startday,
    endday,
    totalrecs,
    successful,
    unsuccessful
    )
if mailnotify == True:
    msg = MIMEMultipart('alternative')
    msg['Subject'] = notifysubj
    msg['From'] = notifyfrom
    msg['To'] = ", ".join(notifyto)
    body = MIMEText(
        notifymesg,
        'plain'
        )
    msg.attach(body)
    server = smtplib.SMTP(
        smtpserver,
        smtpport
        )
    server.ehlo()
    if smtptls:
        try:
            server.starttls()
        except (Exception) as e:
            print("Couldn't start TLS: {}".format(e))
    if smtpauth:
        try:
            server.login(
                smtpuser,
                smtppass
                )
        except (Exception) as e:
            print("Couldn't authenticate to SMTP server: {}".format(e))
    server.set_debuglevel(0)
    server.sendmail(
        notifyfrom,
        notifyto,
        msg.as_string()
        )
    server.quit()
else:
    print(notifymesg)
