# Installation

The WPC-Logger is designed to run on Debian 9 and uses FreeSWITCH 1.8 as the media engine.

## Prerequisites

Run the following commands to install prerequisite packages:

`wget -qO - http://files.freeswitch.org/repo/deb/freeswitch-1.8/fsstretch-archive-keyring.gpg | apt-key add -`

`echo "deb http://files.freeswitch.org/repo/deb/freeswitch-1.8/ stretch main" > /etc/apt/sources.list.d/freeswitch.list`

`echo -e "deb [ trusted=yes ] http://www.deb-multimedia.org stretch main non-free\ndeb-src [ trusted=yes ] http://www.deb-multimedia.org stretch main non-free" > /etc/apt/sources.list.d/multimedia.list`

`apt update`

`apt install deb-multimedia-keyring`

`rm /etc/apt/sources.list.d/multimedia.list`

`echo -e "deb http://www.deb-multimedia.org stretch main non-free\ndeb-src http://www.deb-multimedia.org stretch main non-free" > /etc/apt/sources.list.d/multimedia.list`

`apt update`

`apt install git swig python3-pip python3-dev mysql-server winbind cifs-utils build-essential freeswitch-meta-all freeswitch-mod-shout ntpdate ffmpeg libtag1-dev`

`pip3 install --upgrade setuptools`

`pip3 install python-esl`

`pip3 install pymysql`

`pip3 install pytaglib`

`pip3 install pymssql`

`pip3 install tqdm`

## Get logger package

Clone the repo to you home folder (NOTE: if this repo is still private you'll need to add your SSH key):

`cd ~`

`mkdir dev`

`cd dev`

`git clone https://github.com/westparkcom/Voice-Logger.git`

## Install logger components

We now need to copy all of the logger components in place

`cd Voice-Logger`

`su`

`cp logger.py /usr/local/bin`

`cp loggerconfig.ini.default /usr/local/etc/loggerconfig.ini`

`cp systemd/logger.service /etc/systemd/system`

`cp cron/cdr-rotate /usr/local/bin`

`chmod +x /usr/local/bin/cdr-rotate`

`cp cron/cdr2sql /usr/local/bin`

`cat cron/crontab >> /etc/crontab`

`mkdir /etc/freeswitch/scripts`

`cp lua/logger.lua /etc/freeswitch/scripts`

Modify the file `freeswitch/equeue.xml.example` to point to the IP of you eQueue as well as provide a valid extension with call monitor rights to register as, then copy the file:

`sed -i '/<gateways>/a\<X-PRE-PROCESS cmd="include" data="internal\/*.xml"\/\>' /etc/freeswitch/sip_profiles/internal.xml`

`sed -i 's/<!--<load module="mod_shout"\/>-->/<load module="mod_shout"\/>/g' /etc/freeswitch/autoload_configs/modules.conf.xml`

`mkdir /etc/freeswitch/sip_profiles/internal`

`cp freeswitch/equeue.xml.example /etc/freeswitch/sip_profiles/internal/equeue.xml`

`cp freeswitch/cdr_csv.conf.xml /etc/freeswitch/autoload_configs`

`cp sounds/beep.* /usr/share/freeswitch/sounds`

Restart FreeSWITCH to initialize the changes:

`service freeswitch restart`

## NTP Setup

NTP is important for proper timestamping of recordings. It is recommended to keep in sync with a central NTP server once an hour.

* To use the defult NTP server `pool.ntp.org`:
  * Run the command `cat cron/ntpcron >> /etc/crontab`
* To use a custom NTP server:
  * Modify `cron/ntpcron` and replace `pool.ntp.org` with your own NTP server address
  * Run the command `cat cron/ntpcron >> /etc/crontab`


## Initialize database

Run the following database commands to create the database and create necessary user:

`mysql -u root -p -e "CREATE DATABASE logger;"`

**NOTE: change the `YOURPASSHERE` value to your own password below**

`mysql -u root -p -e "GRANT SELECT,INSERT,UPDATE,DELETE ON logger.* TO logger@'localhost' IDENTIFIED BY 'YOURPASSHERE';"`

Now we need to create the database schema:

`mysql -u root -p logger < mysql/schema.sql`

## Set configuration settings

Modify the `LOGGERDBPASS` setting in `/usr/local/etc/loggerconfig.ini` to reflect the password you chose in the **Initialize database** section

If you wish to receive email notifications if failures occur during SQL import, set the parameters in the `Notification` section according to your needs.

* If you need to send to multiple email addresses, separate them with commas

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

## Restart components

Restart the following components:

`service freeswitch restart`

`service logger restart`

`service cron restart`