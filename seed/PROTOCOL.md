# KE100 "Smart Control" schedule protocol (via KH100 hub)
Seed notes from the original private tooling (tested on KH100 fw 1.8.0, KE100 fw 2.15.0, python-kasa 0.11).
Methods discovered in the Tapo Android app 3.22.105 (TRVRepository); all schedule data is stored locally on the thermostat, proxied by the hub.

All calls go through the hub: `hub._query_helper('control_child', {device_id: <KE100 id>, requestData: {method, params}})`.

## Read
1. `get_sc_schedule_info` (no params) -> `{"enable": bool, "mode": "everyday"|"weekday_sat_sun"|"single_day"}`
2. `get_sc_schedule_rules {"schedule_mode": <mode>, "start_index": 0}` (schedule_mode REQUIRED, else -1008)
   -> `{schedule_mode, day_segment, start_index, sum, schedule_list:[{id:"<mode>:<segment>", rule_list:[{start_min, end_min (inclusive 0..1439), desired_states:{target_temp(int), target_temp_float(°C*10), frost_protection_on, temp_unit}}]}]}`
   Paged: repeat with start_index=len(collected) until == sum. rule_list is NOT sorted; sort by start_min.
   Segment ids: everyday:everyday | weekday_sat_sun:{weekday,saturday,sunday} | single_day:{sunday..saturday}
Calling get_sc_* on the hub itself -> -1002.

## Write (format taken from the Tapo app; used successfully by the original tooling — maintainers should re-verify)
App save order: `set_sc_schedule_info {enable, mode}` FIRST, then one `edit_sc_schedule_rule {schedule_mode, id:"<mode>:<segment>", rule_list}` per segment of the mode.
The device keeps separate stored segments per mode. During the seconds between step 1 and 2 the TRV runs the previously stored segments of the new mode.
App-created schedules can contain 1-minute gaps (device tolerates them); this tool still enforces full contiguous 00:00-23:59 coverage. Temps 5..30 °C, 0.5 steps, or frost protection.

## Dead ends
get_schedule_rules / get_smart_control_schedule / get_trv_multi_mode on child -> -1001. Other working child reads: get_device_info, get_trv_mode, get_early_start, get_frost_protection, get_child_protection.

## Agent recipe (original, to be generalized)
1. Read the room's current schedule and keep its mode. 2. Turn the human's warm blocks into a spec (contiguous HH:MM blocks covering 00:00-23:59; fill gaps with a configurable default temperature; end = minute before next start). Unchanged blocks stay exactly as they are. 3. Dry-run, show before/after per day. 4. Apply with --apply only after the human's explicit yes for this exact change; run once. 5. Read back and confirm every segment matches. One room per apply unless several are named. Never call other hub methods; never print the password. On error: stop and report, don't retry blindly; 3 failures -> stop.
