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
import uuid
import tarfile
import os
import sys
import shutil
from datetime import datetime
import glob
try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
import MySQLdb as mdb
from time import sleep
from tqdm import tqdm

def main():
    # Double verify we actually want to do this
    print("")
    print("###################################################")
    print("#               !!!!!!WARNING!!!!!!               #")
    print("#                                                 #")
    print("# Once you confirm this account archive there     #")
    print("# will not be a way to revert this action!!!!     #")
    print("#                                                 #")
    print("###################################################")
    print("")
    print("Account(s) to be archived:")
    for row in acctIntList:
        print(
            "{}".format(
                row
                )
            )
    print("")
    confirm1 = raw_input(
        "Are you sure you want to archive these accounts? (Y/n): "
        )
    if not (confirm1 == "Y" or confirm1 == "y"):
        print("Not confirmed, aborting...")
        return 0

    print("")
    confirm2 = raw_input(
        "Are you ABSOLUTELY sure you want to archive these accounts? (Y/n): "
        )
    if not (confirm2 == "Y" or confirm2 == "y"):
        print("Not confirmed, aborting...")
        return 0

    nof = {}
    errf = {}
    sqlf = {}

    try:
        archivepath = os.path.join(
            config.get(
                'FreeSWITCH',
                'LOGGERDIR'
                ),
            "archive")
        if not os.path.isdir(archivepath):
            os.makedirs(
                archivepath
                )
        for acct in acctIntList:
            if not os.path.isdir(os.path.join(archivepath, "{}_{}".format(acct, todaysDate))):
                os.makedirs(
                    os.path.join(
                        archivepath,
                        "{}_{}".format(
                            acct,
                            todaysDate
                            )
                        )
                    )
            workingpath = os.path.join(
                archivepath,
                "{}_{}".format(
                    acct,
                    todaysDate
                    )
                )

            nof[str(acct)] = open(
                os.path.join(
                    workingpath,
                    "NoFile.lis"
                    ),
                    'a'
                )
            errf[str(acct)] = open(
                os.path.join(
                    workingpath,
                    "SQLErrors.log"
                    ),
                    'a'
                )
            errf[str(acct)] = open(
                os.path.join(
                    workingpath,
                    "SQLRestore.sql"
                    ),
                    'a'
                )
    except (Exception) as e:
        print("Can't create folders for archival, error: {}".format(e))
        return 1
        
    except (Exception) as e:
        print("Can't open files for writing, error: {}".format(e))
        return 1

    # Connect to DB
    try:
        con = mdb.connect(
            config.get('CDR-Database', 'LOGGERDBSERVER'),
            config.get('CDR-Database', 'LOGGERDBUSER'),
            config.get('CDR-Database', 'LOGGERDBPASS'),
            config.get('CDR-Database', 'LOGGERDB')
            )
        cur = con.cursor()
    except (Exception) as e:
        print("Unable to establish connection to database: {}".format(e))
        print("Aborting...")
        return 1

    # Query for records to delete
    queryResults = []
    for acct in acctIntList:
        if capDateExist:
            sql = "SELECT * FROM {} WHERE ClientID = {}  AND LoggerDate <= '{} 23:59:59';".format(
                config.get('CDR-Database', 'LOGGERDBTABLE'),
                acct,
                capDate
                )
        else:
            sql = "SELECT * FROM {} WHERE ClientID = {};".format(
                config.get('CDR-Database', 'LOGGERDBTABLE'),
                acct
                )
        try:
            cur.execute(sql)
            queryResults.append(cur.fetchall())
        except (Exception) as e:
            print("Unable to execute SQL query: {}".format(e))
            return 1

            
    for items in queryResults:
        for row in tqdm(items):
            relativePath = row[8].replace(
                "{}/".format(
                    config.get('FreeSWITCH', 'LOGGERDIR')
                    ),
                ""
                )
            pathList = relativePath.split("/")
            # Create recording dir, exit if can't
            try:
                loggerPath = os.path.join(
                    os.path.join(
                        archivepath,
                        "{}_{}".format(
                            row[2],
                            todaysDate
                            )
                        ),
                        pathList[0]
                    )
                if not os.path.isdir(loggerPath):
                    os.makedirs(loggerPath)
            except (Exception) as e:
                print("Can't create folders for archival, error: {}".format(e))
                return 1
            sql = "DELETE FROM {} WHERE id={};".format(
                config.get('CDR-Database', 'LOGGERDBTABLE'),
                row[0]
                )
            try:
                archsql = """(Station,ClientID,InboundFlag,DNIS,ANI,CSN,AgentLoginID,AudioFilePath,LoggerDate,AccessTime,UniqueID,Paused) VALUES(
                    {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', {}, '{}', {});""".format(
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        row[7],
                        row[8],
                        row[9],
                        row[10],
                        row[11],
                        row[12]
                    )
                # Kill the record in the DB
                cur.execute(sql)
                sqlf["{}".format(row[2])].write(
                    "{}\n".format(
                        archsql
                        )
                    )
            except (Exception) as e:
                print(
                    "Couldn't delete record ID {} for client ID {} with CSN {}: {}".format(
                        row[0],
                        row[2],
                        row[6],
                        e
                        )
                    )
                print("Adding bad SQL to file...")
                errf["{}".format(row[1])].write(
                    "{}\n".format(
                        sql
                        )
                    )
                

            try:
                sourcePath = row[8]
                destPath = os.path.join(
                    loggerPath,
                    pathList[1]
                    )
                shutil.move(
                    sourcePath,
                    destPath
                    )
            except (Exception) as e:
                print(
                    "Couldn't move file {} to {}: {}".format(
                        sourcePath,
                        destPath,
                        e
                        )
                    )
                print("Adding to NoFile.lis...")
                nof[row[2]].write(
                    "{}\n".format(
                        sourcePath
                        )
                    )
    
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
        tarPath = os.path.join(
            archivepath,
            "{}_{}".format(
                    acct,
                    todaysDate
                )
            )
        outputFile = "{}.tar".format(
            tarPath
            )
        print(
            "Creating tar archive {} and moving all recording to tar archive...".format(
                outputFile
                )
            )
        try:
            with tarfile.open(outputFile, "w") as tar:
                tar.add(
                    tarPath,
                    arcname=os.path.basename(
                        tarPath
                        )
                    )
        except (Exception) as e:
            print("")
            print("Couldn't create tar archive: {}".format(e))
            print("Skipping...")
            print("")
        try:
            shutil.rmtree(
                tarPath
                )
        except (Exception) as e:
            print("")
            print("Couldn't clean up archive files: {}".format(e))
            print("Please delete the folder {} manually when this utility exits...".format(tarPath))
            print("")

    print("")
    print("Archive complete!")
    print("")

if __name__ == "__main__":
    todaysDate = datetime.now().strftime("%Y-%m-%d")

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
        print("")
        print("Error: configuration file location not specified.")
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444 --capdate=2016/10/10".format(sys.argv[0]))
        sys.exit(1)

    try:
        acctPurgeList = argsDict['--accts']
    except:
        print("")
        print("Error: account list not specified.")
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444 --capdate=2016/10/10".format(sys.argv[0]))
        sys.exit(1)

    try:
        capDate = argsDict['--capdate']
        capDateExist = True
    except:
        print("")
        print("Cap date not set, not applying date date restriction")
        print("")
        capDateExist = False
        capDate = "01/01/1970"
        
    if capDateExist:
        try:
            str(datetime.strptime(capDate, "%Y/%m/%d"))
        except:
            print("")
            print("Incorrect date format for --capdate, please use YYYY/MM/DD")
            print("")
            sys.exit(1)

    capDate = capDate.replace(
        "/",
        "-"
        )

    try:
        acctPurgeList = acctPurgeList.replace(
            " ",
            ""
            )
        acctList = acctPurgeList.split(",")
        # Create separate array and force convert to int to make sure we're not getting garbage
        acctIntList = []
        for acct in acctList:
            acctIntList.append(
                int(
                    acct
                    )
                )
    except (Exception) as e:
        print("")
        print("List of accounts invalid, the following error was received: {}").format(e)
        print("")
        print("Usage: python {} --config=/path/to/configfile/loggerconfig.ini --accts=111,222,333,444 --capdate=2016/10/10".format(sys.argv[0]))
        print("")
        print("Aborting...")
        sys.exit(1)


    # Global config
    config = ConfigParser.ConfigParser()
    config.read(loggerConfigFile)
    sys.exit(main())