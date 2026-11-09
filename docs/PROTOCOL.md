# KE100 "Smart Control" schedule protocol (via KH100 hub)

Tested on KH100 firmware 1.8.0, KE100 firmware 2.15.0, and `python-kasa` 0.11.x. Methods were discovered in the Tapo Android app 3.22.105 (`TRVRepository`). Schedule data is stored on the thermostat and proxied through the hub.

All calls use the hub:

```text
hub._query_helper('control_child', {
  'device_id': <KE100 child id>,
  'requestData': {'method': <name>, 'params': <object optional>},
})
```

## Read

1. `get_sc_schedule_info` (no params) → `{ "enable": bool, "mode": "everyday" | "weekday_sat_sun" | "single_day" }`

2. `get_sc_schedule_rules` with `{ "schedule_mode": <mode>, "start_index": 0 }`  
   **`schedule_mode` is required** (otherwise error `-1008`).

   Response shape:

   ```json
   {
     "schedule_mode": "...",
     "day_segment": "...",
     "start_index": 0,
     "sum": <total segments>,
     "schedule_list": [{
       "id": "<mode>:<segment>",
       "rule_list": [{
         "start_min": 0,
         "end_min": 1439,
         "desired_states": {
           "target_temp": 20,
           "target_temp_float": 200,
           "frost_protection_on": false,
           "temp_unit": "celsius"
         }
       }]
     }]
   }
   ```

   **Paging:** call again with `start_index = len(collected schedule_list)` until `start_index >= sum`.

   **Minutes:** `start_min` / `end_min` are inclusive, range `0..1439`. `rule_list` order is not guaranteed — sort by `start_min`.

   **Segment IDs:**

   | mode | segments |
   |------|----------|
   | `everyday` | `everyday` |
   | `weekday_sat_sun` | `weekday`, `saturday`, `sunday` |
   | `single_day` | `sunday` … `saturday` |

Calling `get_sc_*` on the **hub** itself returns `-1002`.

## Write

Save order (matches the Tapo app):

1. `set_sc_schedule_info` with `{ "enable": bool, "mode": <mode> }` — **always first**
2. One `edit_sc_schedule_rule` per segment of that mode:  
   `{ "schedule_mode": <mode>, "id": "<mode>:<segment>", "rule_list": [...] }`

The device stores separate segment data per mode. Between step 1 and step 2 the TRV briefly runs the **previously stored** segments for the new mode.

**Rules enforced by this tool:**

- Contiguous coverage `00:00`–`23:59` (inclusive end minutes; no gaps)
- `target_temp_float = °C × 10` (0.5 °C steps)
- Temperature 5–30 °C or frost protection (`frost_protection_on: true`)
- End minute is **inclusive** (same as the app protocol)

The Tapo app sometimes tolerates 1-minute gaps; this tool still requires full-day coverage.

## Dead ends

On the child, these return `-1001`:

- `get_schedule_rules`
- `get_smart_control_schedule`
- `get_trv_multi_mode`

Other useful child reads: `get_device_info`, `get_trv_mode`, `get_early_start`, `get_frost_protection`, `get_child_protection`.

## Error codes (common)

| Code | Meaning |
|------|---------|
| `-1001` | Method not supported on this device |
| `-1002` | Wrong target (e.g. schedule call on hub, not child) |
| `-1008` | Missing or invalid parameter (e.g. `schedule_mode` omitted) |
