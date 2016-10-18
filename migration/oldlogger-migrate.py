#################################################################
#                                                               #
# Copyright (c) 2016 Westpark Communications, L.P.              #
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
dbserver = "174.46.10.130"
# Microsoft SQL server username
dbusername = "cmdata"
# Microsoft SQL server password
dbpassword = "1234"
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
notifyfrom = "WPC Tech <tech@westparkcom.com>"
# Who to send the email to
notifyto = ["Josh Patten <jpatten@westparkcom.net>"]
# What SMTP server to use
smtpserver = "10.10.10.10"

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
from tqdm import tqdm

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
    print ""
    print "Error: start date not specified or incorrect format."
    print ""
    print "Usage: python", sys.argv[0], "--start=2016/01/01 --end=2016/01/31"
    sys.exit(1)
try:
    endday = argsDict['--end']
    datetime.datetime.strptime(endday, '%Y/%m/%d')
except:
    print ""
    print "Error: end date not specified or incorrect format."
    print ""
    print "Usage: python", sys.argv[0], "--start=2016/01/01 --end=2016/01/31"
    sys.exit(1)
    
notifysubj = "Migration complete for dates " + startday + " to " + endday


try:
    cdrfilename = cdrloc + "/Master.csv." + str(uuid.uuid4())
    f = open(cdrfilename, 'w')
except (Exception) as e:
    print "Can't open file, error:", e
    sys.exit(1)

con = pymssql.connect(dbserver, dbusername, dbpassword, dbdatabase)
cur = con.cursor()
cur.execute("SELECT * FROM [CallLoggerStats] WHERE [LoggerDate] between '" + startday + " 00:00:00' and '" + endday + " 23:59:59'")
rows = cur.fetchall()
outarr = []
dirsdict = {}
for row in tqdm(rows):
    fileloc = row[8].split(stripstring,1)[1]
    convertloc = sourceloc + "/" + fileloc.replace("\\", "/")
    fileloc = fileloc[:-3] + "mp3"
    dircheckloc = destloc + "/" + fileloc.split("\\",1)[0]
    if not dircheckloc in dirsdict:
        dirsdict[dircheckloc] = dircheckloc
    if not os.path.isdir(dircheckloc):
        try:
            print "Creating directory", dircheckloc
            os.makedirs(dircheckloc)
        except (Exception) as e:
            print "Error:", e
            sys.exit(1)
    fileloc = destloc + "/" + fileloc.replace("\\", "/")
    outarr.append('(Station,ClientID,InboundFlag,DNIS,ANI,CSN,AgentLoginID,AudioFilePath,LoggerDate,AccessTime,UniqueID,Paused) VALUES (' + str(row[1]) + ',"' + row[2] + '","' + row[3] + '","' + row[4] + '","' + row[5] + '","' + row[6] + '","' + row[7] + '","' + fileloc + '","' + str(row[0]) + '",' + str(row[10]) + ',"' + str(uuid.uuid4()) + '",0);')
    ffcommand = 'ffmpeg -hide_banner -loglevel fatal -i "' + convertloc + '" -b:a 16k "' + fileloc + '"'
    os.system(ffcommand)
    row = cur.fetchone()
i = 0
for line in outarr:
    i = i + 1
    f.write(line + "\n")    
f.close()
con.close()

uid = pwd.getpwnam(fsuid).pw_uid
gid = grp.getgrnam(fsgid).gr_gid

for key, value in dirsdict.items():
    for root, dirs, files in os.walk(value):
        for direc in dirs:
            os.chown(direc, uid, gid)
        for file in files:
            fname = os.path.join(root, file)
            os.chown(fname, uid, gid)

notifymesg = "Old Logger Migration complete for dates: " + startday + " to " + endday + "\r\nTotal records: " + str(i)

if mailnotify == True:
    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (notifyfrom, ", ".join(notifyto), notifysubj, notifymesg))

    server = smtplib.SMTP(smtpserver)
    server.set_debuglevel(0)
    server.sendmail(notifyfrom, notifyto, msg)
    server.quit()
else:
    print notifymesg