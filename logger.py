import MySQLdb
import SocketServer
import threading
from datetime import date, datetime
import time
import sys
import signal
import subprocess
import socket
import os
import ConfigParser
import logging
import logging.config

# Global config
config = ConfigParser.ConfigParser()
config.read('loggerconfig.ini')

# Logging setup
logging.config.fileConfig('loggerlog.ini')
logwrite = logging.getLogger('loggerLog')

class listenerService(SocketServer.BaseRequestHandler):
    """
    'Thread handler. We only need one thread per connection
    'As PInnacle keeps the connection open and each instance
    'Only deals with one call at a time
    """
    def handle(self):
        try:
            data = 'dummy'
            try:
                logwrite.debug("%s: Connecting to database: HOST: %s | USER: %s | PASS: <removed> | DATABASE: %s" % (str(threading.currentThread()), config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBDB')))
                db = MySQLdb.connect(config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBPASS'), config.get('IMDB', 'IMDBDB'))
                logwrite.info("%s: Database connection successful." % (str(threading.currentThread())))
                c = db.cursor()
                sql = "INSERT INTO %s(thread_id,ip_address,port,timestamp) VALUES('%s','%s',%d,'%s')" % (config.get('IMDB', 'IMDBTABLE'), str(threading.currentThread()), str(self.client_address[0]), self.client_address[1], str(datetime.now()))
                logwrite.debug("%s: Executing SQL: %s" % (str(threading.currentThread()), sql))
                c.execute(sql)
                logwrite.debug("%s: SQL executed successfully." % (str(threading.currentThread())))
                db.commit()
            except Exception as e:
                logwrite.error("%s: Soemthing went wrong while attempting SQL INSERT: %s" % (str(threading.currentThread()), e))
                logwrite.error("%s: Cannot continue, terminating program..." % (str(threading.currentThread())))
                pid = os.getpid()
                os.kill(pid, signal.SIGINT)
                return
            logwrite.info("%s: Client connected from address %s:%s" % (str(threading.currentThread()), self.client_address[0], str(self.client_address[1])))
            while len(data):
                self.request.settimeout(int(config.get('Network', 'TCPTIMEOUT')))
                data = self.request.recv(4096)
                logwrite.debug("%s: Received data: %s" % (str(threading.currentThread()),data))
                # This is where we'll call the objects that will handle what we've received. For now we just echo back...
                self.request.send(data)
            logwrite.info("%s: Client %s:%s disconnected" %(str(threading.currentThread()), self.client_address[0], str(self.client_address[1])))
            sql = "DELETE FROM %s WHERE thread_id='%s'" % (config.get('IMDB', 'IMDBTABLE'), str(threading.currentThread()))
            logwrite.debug("%s: Clearing thread from database: %s" % (str(threading.currentThread()), sql))
            c.execute(sql)
            db.commit()
            db.close
            self.request.close()
            return
        except(socket.timeout):
            logwrite.info("%s: Client %s:%s timed out" %(str(threading.currentThread()), self.client_address[0], str(self.client_address[1])))
            sql = "DELETE FROM %s WHERE thread_id='%s'" % (config.get('IMDB', 'IMDBTABLE'), str(threading.currentThread()))
            logwrite.debug("%s: Clearing thread from database: %s" % (str(threading.currentThread()), sql))
            c.execute(sql)
            db.commit()
            db.close
            self.request.close()
            return
            


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self._shutdown_request = False

try:
    # If we're already listening on port, kill the process
    logwrite.info("Starting up logger")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logwrite.info("Checking to see if port %s is already in use..." %(str(config.get('Network', 'TCPPORT'))))
    result = sock.connect_ex(('127.0.0.1',int(config.get('Network', 'TCPPORT'))))
    if result == 0:
        logwrite.error("Port %s is currently in use. Please ensure logger application is not already running. Exiting..." % (str(config.get('Network', 'TCPPORT'))))
        sys.exit(2)
    else:
        logwrite.info("Port %s is available!" %(str(config.get('Network', 'TCPPORT'))))
    # Try to connect to MySQL DB, exit if you can't
    try:
        logwrite.debug("Connecting to database: HOST: %s | USER: %s | PASS: <removed> | DATABASE: %s" % (config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBDB')))
        db = MySQLdb.connect(config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBPASS'), config.get('IMDB', 'IMDBDB'))
        logwrite.debug("Database connection successful.")
        c = db.cursor()
        logwrite.info("Resetting IMDB...")
        sql = "TRUNCATE %s" % (config.get('IMDB', 'IMDBTABLE'))
        c.execute(sql)
        db.commit()
        db.close()
    except Exception as e:
        logwrite.error("Soemthing went wrong while attempting SQL TRUNCATE: %s" % (e))
        logwrite.error("Cannot continue, terminating program...")
        sys.exit(1)
    # Set up threaded TCP server to serve forever, then start the thread
    logwrite.info("Starting listener service on port %s" % (str(config.get('Network', 'TCPPORT'))))
    t = ThreadedTCPServer(('', int(config.get('Network', 'TCPPORT'))), listenerService)
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
        try:
            logwrite.debug("Connecting to database: HOST: %s | USER: %s | PASS: <removed> | DATABASE: %s" % (config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBDB')))
            db = MySQLdb.connect(config.get('IMDB', 'IMDBHOST'), config.get('IMDB', 'IMDBUSER'), config.get('IMDB', 'IMDBPASS'), config.get('IMDB', 'IMDBDB'))
            logwrite.debug("Database connection successful.")
            c = db.cursor()
            logwrite.info("Clearing IMDB...")
            sql = "TRUNCATE %s" % (config.get('IMDB', 'IMDBTABLE'))
            c.execute(sql)
            db.commit()
            db.close()
            logwrite.warning("Terminating program...")
            sys.exit()
        except Exception as e:
            logwrite.error("Soemthing went wrong while attempting SQL TRUNCATE: %s" % (e))
            logwrite.error("Terminating program...")
            sys.exit()
    else:
        logwrite.warning("Terminating program...")
        sys.exit()
