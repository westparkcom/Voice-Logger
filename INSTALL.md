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

`apt-get install git python-autopep8 python-ESL winbind cifs-utils build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev freeswitch-meta-all freeswitch-mod-shout install python-pip php5 php5-mysql python-dev freetds-dev`

`pip install tqdm`

`pip install pymssql`

TODO: the rest of the installation
