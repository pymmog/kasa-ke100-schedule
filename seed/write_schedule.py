#!/usr/bin/env python3
"""KE100 'Smarte Steuerung' writer – DRY-RUN by default; sends only with --apply.
Usage: write_schedule.py SPEC.json [--apply]
SPEC: {"room":..., "mode":"everyday|weekday_sat_sun|single_day", "enable":true,
       "segments": {"<segment>": [["HH:MM","HH:MM",temp_C|"frost"], ...]}}
Segments per mode: everyday:[everyday] weekday_sat_sun:[weekday,saturday,sunday] single_day:[sunday..saturday]
Protocol (Tapo APK 3.22.105, TRVRepository.Sj -> Tj -> Xj then Vj/Pj -> Qj -> lc):
  1) set_sc_schedule_info {enable, mode}           (app sends this FIRST, always with enable=true from the editor)
  2) edit_sc_schedule_rule {schedule_mode, id:"<mode>:<seg>", rule_list} for every segment of the mode
Rules: end_min inclusive, contiguous, cover 0..1439; target_temp_float = °C*10; 5..30 °C."""
import asyncio, json, os, sys
from kasa import Discover, Credentials
HUB=os.environ['KASA_HOST']; USER=os.environ['KASA_USERNAME']
SEGS={'everyday':['everyday'],'weekday_sat_sun':['weekday','saturday','sunday'],
      'single_day':['sunday','monday','tuesday','wednesday','thursday','friday','saturday']}
def mins(s):
    h,m=map(int,s.split(':')); assert 0<=h<24 and 0<=m<60, s; return h*60+m
def build(blocks,seg):
    rl=[];prev=-1
    for s,e,t in blocks:
        a,b=mins(s),mins(e)
        if a!=prev+1: raise ValueError(f'{seg}: gap/overlap before {s} (prev end {prev})')
        if b<a: raise ValueError(f'{seg}: end before start {s}-{e}')
        prev=b
        if t=='frost': ds={'frost_protection_on':True,'temp_unit':'celsius'}
        else:
            if not 5<=float(t)<=30: raise ValueError(f'{seg}: temp {t} out of 5..30')
            ds={'target_temp':int(t),'target_temp_float':int(round(float(t)*10)),'frost_protection_on':False,'temp_unit':'celsius'}
        rl.append({'start_min':a,'end_min':b,'desired_states':ds})
    if prev!=1439: raise ValueError(f'{seg}: must end at 23:59 (ends {prev})')
    return rl
def validate(spec):
    mode=spec['mode']; assert mode in SEGS, mode
    if set(spec['segments'])!=set(SEGS[mode]): raise ValueError(f'segments must be exactly {SEGS[mode]}')
    return [('set_sc_schedule_info',{'enable':bool(spec.get('enable',True)),'mode':mode})]+\
           [('edit_sc_schedule_rule',{'schedule_mode':mode,'id':f'{mode}:{s}','rule_list':build(spec['segments'][s],s)}) for s in SEGS[mode]]
async def cc(hub,cid,m,p=None):
    rq={'method':m}
    if p is not None: rq['params']=p
    r=(await hub._query_helper('control_child',{'device_id':cid,'requestData':rq}))['control_child']['responseData']
    if r.get('error_code')!=0: raise RuntimeError(f'{m}: error {r.get("error_code")}')
    return r.get('result')
async def read_mode(hub,cid,mode):
    out=[];i=0
    while True:
        r=await cc(hub,cid,'get_sc_schedule_rules',{'schedule_mode':mode,'start_index':i})
        out+=r.get('schedule_list') or []; i=len(out)
        if i>=r.get('sum',0) or not r.get('schedule_list'): return out
async def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]; apply='--apply' in sys.argv
    if not args: sys.exit(__doc__)
    spec=json.load(open(args[0]))
    try: reqs=validate(spec); print('VALIDATION: OK –',len(reqs),'requests')
    except Exception as e: sys.exit(f'VALIDATION FAILED: {e}')
    pw=os.environ['KASA_PASSWORD']
    hub=await Discover.discover_single(HUB,credentials=Credentials(USER,pw)); await hub.update()
    try:
        ch=[c for c in hub.children if c.alias==spec['room']][0]
        info=await cc(hub,ch.device_id,'get_sc_schedule_info'); print('CURRENT info:',info)
        try:
            ex=await read_mode(hub,ch.device_id,spec['mode'])
            print(f"CURRENT stored {spec['mode']} segments: {[s['id'] for s in ex]}")
            for s in ex: print('  ',s['id'],[(r['start_min'],r['end_min'],r['desired_states'].get('target_temp_float')) for r in sorted(s['rule_list'],key=lambda r:r['start_min'])])
        except Exception as e: print('CURRENT stored segments for target mode: n/a –',e)
        for m,p in reqs:
            print(f'\n>>> control_child device_id={ch.device_id} method={m}\n'+json.dumps(p,ensure_ascii=False))
            if apply: print('RESULT:',await cc(hub,ch.device_id,m,p))
        if not apply: print('\nDRY-RUN – nothing sent. Re-run with --apply to send.')
    finally: await hub.disconnect()
asyncio.run(main())
