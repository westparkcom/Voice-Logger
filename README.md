# WPC-Logger

The WPC-Logger project is a call recording system intended for use with Professional Teledata's PInnacle platform, and the eOn eQueue platform. This project only provides the backend recording system with database. A frontend system will need to be devised in order to access the recordings.

## Why WPC-Logger

Over time there have been several problems realized with the old logger systems installed for use with PInnacle:

* Per-port costs for the old logger system are prohibitively expensive.
* The old logger system does not gracefully deal with missing data. This can cause numerous issues:
  * Overlapping call recordings happen when PInnacle sends a START command without having first sent a STOP command. This causes situations where one call an agent just took will simply roll into another call. This is a huge HIPAA compliance issue.
  * When calls are parked and then resumed, PInnacle does not send a DNIS with the new START command. This was causing recordings for calls that were paused and resumed after being parked to fail.
* The old logger system appears to discard recordings that are less than 15 seconds, but inserts the record in the database anyway. This causes recordings to appear to be missing.
* The old logger system is limited to WAV and WMA formats for storing recordings. Most platforms support playing WAV from browsers, but WMA is far less supported. 

WPC-Logger aims to solve those problems. Some of the advantages WPC-Logger has over the old logger system are:

* There are no port costs or any licensing costs required. The entire platform is royalty free.
* The WPC-Logger platform is open source, meaning you can modify the platform to fit your needs, provided you adhere to the [LICENSE](LICENSE.md).
* The WPC-Logger platform is designed to work around missing information. For example:
  * If PInnacle sends a START command for an agent ID without having first sent a STOP command, WPC-Logger is designed to search for existing recordings for that agent ID and terminate those recordings before starting a new recording.
  * If WPC-Logger received a START command without a DNIS, one is filled in automatically
* The WPC-Logger system does not discard ANY recordings
* The WPC-Logger system defaults to recording in MP3 format, which is compatible with almost every device and browser while being significantly smaller than WAV. Other formats are available, such as OGG and WAV

## Installation

See [INSTALL](INSTALL.md) for installation instructions

## Usage

See [USAGE](USAGE.md) for information on how to configure PInnacle to use the WPC-Logger system.

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

## Credits

* Josh Patten - Westpark Communications
* Tim Fey - Westpark Communications
* Sky Knippa - Westpark Communications

## License

See [LICENSE](LICENSE.md) for license information
