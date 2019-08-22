------------------------------------------------------------------
--                                                              --
-- Copyright (c) 2016 Westpark Communications, L.P.             --
-- Subject to the GNU Affero GPL license                        --
-- See the file LICENSE.md for details                          --
--                                                              --
------------------------------------------------------------------
max_calls = session:getVariable("max_calls")
gw_name = session:getVariable("gw_name")
session:answer()
session:execute("limit", "hash logger gw_" .. gw_name .. " " .. max_calls)
current_uuid = session:getVariable("uuid")
agent_id = session:getVariable("agent_id")
agent_login_id = session:getVariable("agent_login_id")
call_dnis = session:getVariable("call_dnis")
call_ani = session:getVariable("call_ani")
call_type = session:getVariable("call_type")
call_csn = session:getVariable("call_csn")
call_acct = session:getVariable("call_acct")
recording_file = session:getVariable("recording_file")
max_calls = session:getVariable("max_calls")

session:setVariable("RECORD_TITLE", "CSN: " .. call_csn .. " | ACCT: " .. call_acct .. " | AGENTID: " .. agent_id)
session:setVariable("RECORD_ARTIST", agent_login_id)
session:setVariable("RECORD_DATE", os.date("%x %X"))
session:setVariable("RECORD_COMMENT", "DNIS: " .. call_dnis .. " | ANI: " .. call_ani .. " | TYPE: " .. call_type)
session:setVariable("RECORD_STEREO", "false")
session:setVariable("RECORD_HANGUP_ON_ERROR", "true")
session:setVariable("record_waste_resources", "true")
session:setVariable("playback_terminators", "none")
session:execute("record_session", recording_file)
session:execute("endless_playback", "silence_stream://-1")
session:hangup()
