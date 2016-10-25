# Usage

To utilize the WPC-Logger system after installation and configuration you will need to set you PInnacle INI file settings. Find and modify the following settings to match your environment:

    PITAS_LOGGER_TCPIP_ADDRESS         = 10.10.10.10
    PITAS_LOGGER_TCPIP_PORT            = 8091
    PITAS_LOGGER_CENTURISOFT           = YES
    PITAS_LOGGER_PERSISTENT_CONNECTION = YES
    PITAS_LOGGER_MACHINE               = 1
    PITAS_LOGGER_TCPIP_ATTEMPTS        = 5
    PITAS_LOGGER_RECORD_DURATION       =
    PITAS_LOGGER_CLIENT_ID_FIELD       = fldClientID
    PITAS_LOGGER_DNIS_FIELD            = fldDNIS
    PITAS_LOGGER_DNIS_LENGTH           = 4
    PITAS_LOGGER_ANI_FIELD             = fldANI
    PITAS_LOGGER_CSN_FIELD             = fldCSN
    PITAS_LOGGER_AGENT_FIELD           = fldAgentLoginID
    PITAS_LOGGER_VOXFILE_FIELD         = fldCallName
    PITAS_LOGGER_CALL_TYPE_FIELD       = fldCallType
    PITAS_LOGGER_SYNCRONOUS            = NO
    PITAS_LOGGER_SHOW_WINDOW           = NO

The settings you need to focus on are:

Variable | Description
--- | ---
PITAS_LOGGER_TCPIP_ADDRESS | The IP address of your WPC-Logger system.
PITAS_LOGGER_TCPIP_PORT | The port number used by your WPC-Logger system. Default is 8091.
PITAS_LOGGER_CENTURISOFT | Set to **YES**. We emulate this protocol set.
PITAS_LOGGER_PERSISTENT_CONNECTION | Set to **YES**. Though WPC-Logger closes connections immediately after sending a response, leaving this value set to **YES** ensures proper operation.

The rest of these settings should remain as-is. After making these changes, restart PInnacle client and all logger requests will now go to your new WPC-Logger system.
