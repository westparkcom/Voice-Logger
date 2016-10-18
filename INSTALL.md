# Installation

The WPC-Logger is designed to run on Debian 8 and uses FreeSWITCH as a media engine.

## Prerequisites

Run the following commands to install prerequisite packages:

`wget -O - https://files.freeswitch.org/repo/deb/debian/freeswitch_archive_g0.pub | apt-key add -`

`echo "deb http://files.freeswitch.org/repo/deb/freeswitch-1.6/ jessie main" > /etc/apt/sources.list.d/freeswitch.list`

`echo -e "deb http://www.deb-multimedia.org jessie main non-free\ndeb-src http://www.deb-multimedia.org jessie main non-free" > /etc/apt/sources.list.d/multimedia.list`

`apt-get update`

`apt-get install deb-multimedia-keyring`

`apt-get update`

`apt-get remove ffmpeg`

`apt-get install git python-autopep8 python-ESL mysql-server winbind cifs-utils build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev freeswitch-meta-all freeswitch-mod-shout python-pip php5 php5-mysql python-dev freetds-dev`

Note that you'll need to set you MySQL root password. Don't forget it as you'll need it later!

`pip install tqdm`

`pip install pymssql`

## Get logger package

Clone the repo to you home folder (NOTE: if this repo is still private you'll need to add your SSH key):

`cd ~`

`mkdir dev`

`cd dev`

`git clone git@github.com:westparkcom/Voice-Logger.git`

## Install logger components

We now need to copy all of the logger components in place

`cd Voice-Logger`

`su`

`cp logger.py /usr/local/bin`

`cp loggerlog.ini.default /usr/local/etc/loggerlog.ini`

`cp loggerconfig.ini.default /usr/local/etc/loggerconfig.ini`

`cp systemd/logger.service /etc/systemd/system/multi-user.target.wants`

`cp cron/cdr-rotate /usr/local/bin`

`chmod +x /usr/local/bin/cdr-rotate`

`cp cron/cdr2mysql /usr/local/bin`

`cat cron/crontab >> /etc/crontab`

`mkdir /etc/freeswitch/scripts`

`cp lua/logger.lua /etc/freeswitch/scripts`

Modify the file `freeswitch/equeue.xml.example` to point to the IP of you eQueue as well as provide a valid extension with call monitor rights to register as, then copy the file:

`cp freeswitch/equeue.xml.example /etc/freeswitch/sip_profiles/internal`

`cp freeswitch/cdr_csv.conf.xml /etc/freeswitch/autoload_configs`

## Initialize database

Run the following database commands to create the database and create necessary user:

`mysql -u root -p -e "CREATE DATABASE logger;"`

**NOTE: change the `YOURPASSHERE` value to your own password below**

`mysql -u root -p -e "GRANT SELECT,INSERT,UPDATE,DELETE ON logger TO logger@'localhost' IDENTIFIED BY 'YOURPASSHERE';"`

Now we need to create the database schema:

`mysql -u root -p logger < mysql/schema.sql`

## Set configuration settings

Modify the `LOGGERDBPASS` setting in `/usr/local/etc/loggerconfig.ini` to reflect the password you chose in the **Initialize database** section

## Create necessary directories

We need to create the log file directory:

`mkdir /var/log/logger`

We also need to create the folder for storing the recordings. This can be used to:

* Store the files directly on the file system if you intend to host the files directly from the logger server, or
* Mount a shared drive for the files to be placed (recommended). Mounting a shared drive is beyond the scope of this installation manual

For this installation, we will create the folder directly on the filesystem:

`mkdir /usr/share/freeswitch/sounds/logger`

We need to set filesystem permissions so that FreeSWITCH can write to the folder:

`chown -R freeswitch:freeswitch /usr/share/freeswitch/sounds/logger`

## Enable logger and FreeSWITCH to start on boot

`systemctl enable logger`

`systemctl enable freeswitch`

TODO: the rest of the installation
