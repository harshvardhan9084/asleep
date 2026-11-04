#!/usr/bin/env python3
"""probe_b31_flags3.py — spot-check borderline adjudications with verbatim evidence."""
import csv, json, re

BASE = '/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv'
DRAFTS = '/home/z/my-project/work/pipeline_v2/drafts/'
B30 = '/home/z/my-project/scripts/pipeline_v2/drafts_B30/'

rows = {r['subject_id']: r for r in csv.DictReader(open(BASE))}

def words(s):
    return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()

DISTINCTIVE = set("""simplex transportation assignment sequencing queuing pert cpm inventory forecasting
mrp JIT scheduling cellular group layout aggregate capacity demand work-study ergonomics
polymers polymerization composites ceramics nano sintering gis remote sensing gps surveying
photogrammetry cartography mine mines ventilation gases dust subsidence roof strata
robotics automation plc scada actuators sensors kinematics gripper end-effector
welding casting forming machining metrology tolerance gauge""".split())

def distinctive(draft_txt, row_txt):
    dw, rw = set(words(draft_txt)), set(words(row_txt))
    shared = {w for w in dw & rw if w in DISTINCTIVE}
    return sorted(shared)

def show(tag, a, b, n=160):
    print(f"  {tag}:")
    print(f"    draft u1: {a[:n]!r}")
    print(f"    row   u1: {b[:n]!r}")

print("=== 01::18 Production Planning and Control vs production-planning-control (EPI-501)")
s = json.load(open(DRAFTS + '01_btech_mfg-tech_y3_syllabus_2018-19.draft.json'))['subjects'][18]
r = rows['production-planning-control']
print("  distinctive shared:", distinctive(' '.join(s['units'].values()), ' '.join((r.get(f'unit{k}_text') or '') for k in range(1,6))))
show('u1', s['units'].get('1',''), r.get('unit1_text') or '')

print("=== 01::26 Operation Research vs operations-research (NOE073)")
s = json.load(open(DRAFTS + '01_btech_mfg-tech_y3_syllabus_2018-19.draft.json'))['subjects'][26]
r = rows['operations-research']
print("  distinctive shared:", distinctive(' '.join(s['units'].values()), ' '.join((r.get(f'unit{k}_text') or '') for k in range(1,6))))
show('u1', s['units'].get('1',''), r.get('unit1_text') or '')

print("=== 02::01 Automation & Robotics (RPI701) vs B30 doc04 subject 11 (2019-20 ME DE print)")
s = json.load(open(DRAFTS + '02_btech_mfg-tech_y4_syllabus-cbcs_2019-20.draft.json'))['subjects'][1]
b30 = json.load(open(B30 + '04_btech_me_y4_syllabus-cbcs_2019-20.draft.json'))
b11 = [x for x in b30['subjects'] if x.get('name','').lower().startswith('automation')][0]
print("  b30 subject name:", b11['name'], "codes:", b11.get('codes'))
def jac(a, b):
    wa, wb = set(words(a)), set(words(b))
    return len(wa & wb) / len(wa | wb) if wa | wb else 0
for k in sorted(set(s['units']) & set(b11['units'])):
    print(f"    unit{k}: J={jac(s['units'][k], b11['units'][k]):.2f}")
show('u1', s['units'].get('1',''), b11['units'].get('1',''))

print("=== 02::05 Advanced Material Technology (RPI070) vs advanced-materials-technology (2009-10)")
s = json.load(open(DRAFTS + '02_btech_mfg-tech_y4_syllabus-cbcs_2019-20.draft.json'))['subjects'][5]
r = rows['advanced-materials-technology']
print("  row name:", r['subject_name'], "| sess:", r['effective_session_latest'], "| primary:", repr(r['primary_code']))
print("  distinctive shared:", distinctive(' '.join(s['units'].values()), ' '.join((r.get(f'unit{k}_text') or '') for k in range(1,6))))
show('u1', s['units'].get('1',''), r.get('unit1_text') or '')

print("=== 06::16 Geo-Informatics (BMN-062) vs geoinformatics (ECE402 2009-10)")
s = json.load(open(DRAFTS + '06_btech_mining_y3_syllabus_2025-26.draft.json'))['subjects'][16]
r = rows['geoinformatics']
print("  distinctive shared:", distinctive(' '.join(s['units'].values()), ' '.join((r.get(f'unit{k}_text') or '') for k in range(1,6))))
show('u1', s['units'].get('1',''), r.get('unit1_text') or '')

print("=== 10::04 Polymer Science and Technology (2009-10 draft) vs polymer-science-and-technology (2023-24 BOE311)")
s = json.load(open(DRAFTS + '10_btech_open-electives-science_2009-10.draft.json'))['subjects'][4]
r = rows['polymer-science-and-technology']
print("  draft units:", len(s['units']), "row units:", sum(1 for k in range(1,6) if r.get(f'unit{k}_text')))
print("  distinctive shared:", distinctive(' '.join(s['units'].values()), ' '.join((r.get(f'unit{k}_text') or '') for k in range(1,6))))
show('u1', s['units'].get('1',''), r.get('unit1_text') or '')

print("=== 01::24 Product Design and Development: does product-development-and-design row exist?")
r = rows.get('product-development-and-design')
if r:
    print("  YES:", r['subject_name'], '| sess:', r['effective_session_latest'], '| primary:', r['primary_code'], '| all:', (r['all_codes'] or '')[:70])
else:
    print("  NO ROW")
