#!/usr/bin/python

import uuid
import tarfile
import os
import sys
import shutil
from datetime import datetime
import glob
import ConfigParser
import MySQLdb as mdb
from time import sleep
from tqdm import tqdm

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
    loggerConfigFile = argsDict['--config']
except:
    print ""
    print "Error: configuration file location not specified."
    print ""
    print "Usage: python", sys.argv[0], "--config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444 --capdate=2016/10/10"
    sys.exit(1)

try:
    acctPurgeList = argsDict['--accts']
except:
    print ""
    print "Error: account list not specified."
    print ""
    print "Usage: python", sys.argv[0], "--config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444 --capdate=2016/10/10"
    sys.exit(1)

try:
    capDate = argsDict['--capdate']
    capDateExist = True
except:
    print ""
    print "Cap date not set, not applying date date restriction"
    print ""
    capDateExist = False
    
if capDateExist:
    try:
        datetime.strptime(capDate, "%Y/%m/%d")
    except:
        print ""
        print "Incorrect date format for --capdate, please use YYYY/MM/DD"
        print ""
        sys.exit(1)

capDate = capDate.replace("/", "-")

try:
    acctPurgeList = acctPurgeList.replace(" ", "")
    acctList = acctPurgeList.split(",")
    # Create separate array and force convert to int to make sure we're not getting garbage
    acctIntList = []
    for acct in acctList:
        acctIntList.append(int(acct))
except (Exception) as e:
    print ""
    print "List of accounts invalid, the following error was received:", e
    print ""
    print "Usage: python", sys.argv[0], "--config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444"
    print ""
    print "Aborting..."
    sys.exit(1)


# Global config
config = ConfigParser.ConfigParser()
config.read(loggerConfigFile)

# Double verify we actually want to do this
print ""
print "###################################################"
print "#               !!!!!!WARNING!!!!!!               #"
print "#                                                 #"
print "# Once you confirm this account archive there     #"
print "# will not be a way to revert this action!!!!     #"
print "#                                                 #"
print "###################################################"
print ""
print "Account(s) to be archived:"
for row in acctIntList:
    print str(row)
print ""
confirm1 = raw_input("Are you sure you want to archive these accounts? (Y/n): ")
if not (confirm1 == "Y" or confirm1 == "y"):
    print "Not confirmed, aborting..."
    sys.exit(0)

print ""
confirm2 = raw_input("Are you ABSOLUTELY sure you want to archive these accounts? (Y/n): ")
if not (confirm2 == "Y" or confirm2 == "y"):
    print "Not confirmed, aborting..."
    sys.exit(0)

nof = {}
errf = {}
sqlf = {}

try:
    archivepath = str(config.get('FreeSWITCH', 'LOGGERDIR')) + "/archive"
    if not os.path.isdir(archivepath):
        os.makedirs(archivepath)
    for acct in acctIntList:
        if not os.path.isdir(archivepath + "/" + str(acct)):
            os.makedirs(archivepath + "/" + str(acct))
        nof[str(acct)] = open(archivepath + "/" + str(acct) + "/NoFile.lis", 'a')
        errf[str(acct)] = open(archivepath + "/" + str(acct) + "/SQLErrors.log", 'a')
        sqlf[str(acct)] = open(archivepath + "/" + str(acct) + "/SQLRestore.sql", 'a')
except (Exception) as e:
    print "Can't create folders for archival, error:", e
    sys.exit(1)
    
except (Exception) as e:
    print "Can't open files for writing, error:", e
    sys.exit(1)

# Connect to DB
try:
    con = mdb.connect(str(config.get('CDR-Database', 'LOGGERDBSERVER')), str(config.get('CDR-Database', 'LOGGERDBUSER')), str(config.get('CDR-Database', 'LOGGERDBPASS')), str(config.get('CDR-Database', 'LOGGERDB')))
    cur = con.cursor()
except (Exception) as e:
    print "Unable to establish connection to database:", e
    print "Aborting..."
    sys.exit(1)

# Query for records to delete
queryResults = []
for acct in acctIntList:
    if capDateExist:
        sql = "SELECT * FROM " + str(config.get('CDR-Database', 'LOGGERDBTABLE')) + " WHERE ClientID = " + str(acct) + " AND LoggerDate <= '" + str(capDate) + " 23:59:59';"
    else:
        sql = "SELECT * FROM " + str(config.get('CDR-Database', 'LOGGERDBTABLE')) + " WHERE ClientID = " + str(acct) + ";"
    try:
        cur.execute(sql)
        queryResults.append(cur.fetchall())
    except (Exception) as e:
        print "Unable to execute SQL query:", e
        sys.exit(1)

        
for items in queryResults:
    for row in tqdm(items):
        relativePath = row[8].replace(str(config.get('FreeSWITCH', 'LOGGERDIR')) + "/", "")
        pathList = relativePath.split("/")
        # Create recording dir, exit if can't
        try:
            loggerPath = archivepath + "/" + str(row[2]) + "/" + pathList[0]
            if not os.path.isdir(loggerPath):
                os.makedirs(loggerPath)
        except (Exception) as e:
            print "Can't create folders for archival, error:", e
            sys.exit(1)
        sql = "DELETE FROM " + str(config.get('CDR-Database', 'LOGGERDBTABLE')) + " WHERE id=" + str(row[0]) + ";"
        
        try:
            archsql = '(Station,ClientID,InboundFlag,DNIS,ANI,CSN,AgentLoginID,AudioFilePath,LoggerDate,AccessTime,UniqueID,Paused) VALUES (' + str(row[1]) + ',"' + row[2] + '","' + row[3] + '","' + row[4] + '","' + row[5] + '","' + row[6] + '","' + row[7] + '","' + row[8] + '","' + str(row[9]) + '",' + str(row[10]) + ',"' + str(row[11]) + '",' + str(row[12]) + ");"
            # Kill the record in the DB
            cur.execute(sql)
            sqlf[str(row[2])].write(archsql + "\n")
        except (Exception) as e:
            print "Couldn't delete record ID", str(row[0]), "for client ID", str(row[2]) , "with CSN", str(row[6]), ":", e
            print "Adding bad SQL to file..."
            errf[str(row[1])].write(sql + "\n")
            

        try:
            sourcePath = row[8]
            destPath = loggerPath + "/" + pathList[1]
            shutil.move(sourcePath, destPath)
        except (Exception) as e:
            print "Couldn't move file", sourcePath, "to", destPath, ":", e
            print "Adding to NoFile.lis..."
            nof[row[2]].write(sourcePath + "\n")
 
con.commit()
con.close()

# Close all open files
for acct in acctIntList:
    nof[str(acct)].close()
    errf[str(acct)].close()
    sqlf[str(acct)].close()
    
# Tar everything up here
sleep(1)
for acct in acctIntList:
    tarPath = archivepath + "/" + str(acct)
    outputFile = tarPath + ".tar"
    try:
        with tarfile.open(outputFile, "w") as tar:
            tar.add(tarPath, arcname=os.path.basename(tarPath))
    except (Exception) as e:
        print ""
        print "Couldn't create tar archive:", e
        print "Skipping..."
        print ""
    try:
        shutil.rmtree(tarPath)
    except (Exception) as e:
        print ""
        print "Couldn't clean up archive files:", e
        print "Please delete the folder", tarPath, "when this utility exits..."
        print ""

print ""
print "Archive complete!"
print ""