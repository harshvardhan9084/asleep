import json, re, sys

BASE = '/home/z/my-project/work/pipeline_v2'
d = json.load(open(BASE + '/parsed/04_bpharm_scheme-syllabus_2026-27.json'))

BOIL1 = re.compile(r'B\. Pharm\. Syllabus\s*\n\s*\d*\s*\n')
BOIL2 = re.compile(r'Evaluation Scheme Bachelor of Pharmacy I, II, III & IV Year syllabus 2026-2027\s*\n')

def clean(t):
    t = BOIL2.sub('', t)
    t = BOIL1.sub('', t)
    return t

# concatenate cleaned pages, keeping page start markers for locators
segs = []   # subject segments
pages = []  # non-subject page texts by no
for p in d['pages']:
    pages.append((p['no'], clean(p['text'])))

HDR = re.compile(r'Course Code\s*\nCourse Title\s*\nCourse Type\s*\n')
# find subject start anchors across page-concatenated text with page map
full = ''
pagemarks = []  # (pos, pageno)
for no, t in pages:
    pagemarks.append((len(full), no))
    full += t + '\n'

def page_of(pos):
    last = 1
    for st, no in pagemarks:
        if st <= pos: last = no
        else: break
    return last

starts = [m.start() for m in HDR.finditer(full)]
print('anchor count:', len(starts), file=sys.stderr)
subs = []
for i, s in enumerate(starts):
    e = starts[i+1] if i+1 < len(starts) else len(full)
    seg = full[s:e]
    subs.append((page_of(s), seg))

json.dump([{'page': p, 'seg': seg} for p, seg in subs], open(BASE + '/parsed/b04_segments.json', 'w'))
# compact listing
for p, seg in subs:
    first = seg.split('\n')
    code = first[3].strip() if len(first) > 3 else '?'
    print(p, '|', code)
