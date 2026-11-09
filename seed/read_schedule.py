#!/usr/bin/env python3
"""READ-ONLY: print KE100 'Smarte Steuerung' schedules via KH100 control_child.
Methods from Tapo APK 3.22.105 (com/tplink/libtapoiotapi/repository/child/TRVRepository.java):
  get_sc_schedule_info  -> {enable, mode}  mode in everyday|weekday_sat_sun|single_day
  get_sc_schedule_rules {schedule_mode, start_index} -> {schedule_mode, day_segment, start_index, sum, schedule_list}
Usage: read_schedule.py [--json]   (also writes ./schedules.json)"""
import asyncio, json, os, sys
from kasa import Discover, Credentials
HUB=os.environ['KASA_HOST']; USER=os.environ['KASA_USERNAME']
async def cc(hub,cid,m,p=None):
    rq={'method':m}
    if p is not None: rq['params']=p
    r=(await hub._query_helper('control_child',{'device_id':cid,'requestData':rq}))['control_child']['responseData']
    if r.get('error_code')!=0: raise RuntimeError(f'{m} {p}: error {r.get("error_code")}')
    return r.get('result')
def hm(m): return f'{m//60:02d}:{m%60:02d}'
def temp(ds):
    if ds.get('frost_protection_on'): return 'frost protection'
    f=ds.get('target_temp_float'); return f'{f/10:.1f} °C' if f is not None else f"{ds.get('target_temp')} °C"
async def rules(hub,cid,mode):
    out=[];idx=0
    while True:
        r=await cc(hub,cid,'get_sc_schedule_rules',{'schedule_mode':mode,'start_index':idx})
        out+=r.get('schedule_list',[]); idx=len(out)
        if idx>=r.get('sum',0) or not r.get('schedule_list'): return r,out
async def main():
    pw=os.environ['KASA_PASSWORD']
    hub=await Discover.discover_single(HUB,credentials=Credentials(USER,pw)); await hub.update()
    dump={}
    try:
        for ch in hub.children:
            info=await cc(hub,ch.device_id,'get_sc_schedule_info')
            print(f"=== {ch.alias}: enabled={info.get('enable')} mode={info.get('mode')}")
            try: meta,sl=await rules(hub,ch.device_id,info.get('mode'))
            except Exception as e: print('  ',e); continue
            dump[ch.alias]={'device_id':ch.device_id,'info':info,'schedule_list':sl}
            for s in sl:
                print(f"  [{s['id'].split(':',1)[-1]}]")
                for r in sorted(s.get('rule_list',[]),key=lambda r:r['start_min']):
                    print(f"    {hm(r['start_min'])}-{hm(r['end_min'])}  {temp(r.get('desired_states',{}))}")
    finally: await hub.disconnect()
    if '--json' in sys.argv: print(json.dumps(dump,ensure_ascii=False,indent=1))
    json.dump(dump,open('schedules.json','w'),ensure_ascii=False,indent=1)
asyncio.run(main())
