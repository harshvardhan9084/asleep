"""Rebuild page texts with OCR recovery of image-printed fragments (RULES §6).
Base = raw PyMuPDF text (content-stream order). Image fragments are inserted
inline (between neighbour spans of the vertically-overlapping text line) or as
their own line (after the nearest preceding line). All fragments logged."""
import fitz, subprocess, tempfile, os, json, re

PDF = '/home/z/my-project/work/pipeline_v2/staging/batch04/04_bpharm_scheme-syllabus_2026-27.pdf'
OUT = '/home/z/my-project/work/pipeline_v2/parsed/b04_pages_corrected.json'
OCRLOG = '/home/z/my-project/work/pipeline_v2/parsed/b04_ocr_fragments.json'

doc = fitz.open(PDF)

def ocr(page, rect):
    pix = page.get_pixmap(matrix=fitz.Matrix(8, 8), clip=fitz.Rect(rect))
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(pix.tobytes('png')); fn = f.name
    out = subprocess.run(['tesseract', fn, '-', '--psm', '6'], capture_output=True, text=True)
    os.unlink(fn)
    t = re.sub(r'\s+', ' ', out.stdout).strip()
    return t

def normkey(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())[:30]

corrected, ocrlog = {}, []
for pno in range(len(doc)):
    page = doc[pno]
    H = page.rect.height
    raw = page.get_text()
    rd = page.get_text('dict')
    lines = []  # content order
    for b in rd['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            if l['bbox'][1] < 72 or l['bbox'][3] > H - 42: continue
            spans = [(s['bbox'][0], s['bbox'][2],
                      ''.join(ch.get('c','') for ch in s.get('chars', [])) if 'chars' in s else s.get('text',''))
                     for s in l['spans']]
            lines.append({'bbox': l['bbox'], 'spans': spans})
    cands = []
    for inf in page.get_image_info(xrefs=True):
        bx = inf['bbox']; h = bx[3]-bx[1]; w = bx[2]-bx[0]
        if 5 < h < 100 and w > 18:
            cands.append(bx)
    if not cands:
        # still filter furniture from raw crudely: drop 'B. Pharm. Syllabus' header + page no lines
        out_lines = []
        for ln in lines:
            t = ' '.join(sp[2].strip() for sp in ln['spans'] if sp[2].strip())
            out_lines.append(t)
        corrected[pno+1] = '\n'.join(out_lines) + '\n'
        continue
    # per-fragment placement
    edits = []  # (anchor_raw_text, insert_after_bool, text)
    for bx in cands:
        t = ocr(page, bx)
        if not t or len(re.sub(r'[^A-Za-z0-9]', '', t)) < 2: continue
        if t == 'L. | so': t = 'LD50.'   # p88 subscript 50, OECD 425 context (§4 brain clause)
        best, bestov = None, 0
        for ln in lines:
            ov = min(ln['bbox'][3], bx[3]) - max(ln['bbox'][1], bx[1])
            if ov > bestov: bestov, best = ov, ln
        frag = {'page': pno+1, 'rect': [round(v,1) for v in bx], 'text': t}
        if best and bestov > 2:
            lspans = best['spans']
            lefts = [sp for sp in lspans if sp[1] <= bx[0] + 2]
            rights = [sp for sp in lspans if sp[0] >= bx[2] - 2]
            if lefts:
                anchor = lefts[-1][2].strip()
                # strip trailing period of OCR if right neighbour starts with '. '
                if rights and rights[0][2].lstrip().startswith('. ') and t.endswith('.'):
                    t = t[:-1].rstrip()
                frag['mode'] = 'inline'
                edits.append((anchor, True, t))
            elif rights:
                anchor = rights[0][2].strip()
                if t.endswith('.') and anchor.lstrip().startswith('. '):
                    t = t[:-1].rstrip()
                frag['mode'] = 'inline-before'
                edits.append((anchor, False, t))
            else:
                frag['mode'] = 'line-end'
                edits.append((lspans[-1][2].strip(), True, t))
        else:
            above = [ln for ln in lines if ln['bbox'][3] <= bx[1] + 2]
            anchor = ' '.join(sp[2].strip() for sp in above[-1]['spans']).strip() if above else ''
            frag['mode'] = 'ownline'
            edits.append((anchor, True, t))
        ocrlog.append(frag)
    # apply edits to raw with a moving cursor
    for anchor, after, t in edits:
        nk = normkey(anchor)
        pos = raw.find(anchor)
        if pos < 0:
            pos = None
            step = 0
        elif after:
            pos = pos + len(anchor)
        if pos is None:
            # fuzzy: find anchor chars collapsed
            raw2 = raw
            found = False
            for m in re.finditer(re.escape(anchor[:12]) if len(anchor) >= 12 else re.escape(anchor), raw):
                found = True; pos = m.end() if after else m.start(); break
            if not found:
                pos = 0
        ins = (' ' + t) if after else (t + ' ')
        raw = raw[:pos] + ins + raw[pos:]
    corrected[pno+1] = raw

json.dump(corrected, open(OUT, 'w'))
json.dump(ocrlog, open(OCRLOG, 'w'), indent=0)
from collections import Counter
print('pages:', len(corrected), 'fragments:', len(ocrlog), Counter(f['mode'] for f in ocrlog))
