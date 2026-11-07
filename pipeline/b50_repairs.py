#!/usr/bin/env python3
"""b50_repairs.py — B50 draft repairs:
1. Atomic code normalization (slash-joined compound prints, en-dashes) for 01/02/03/05/06.
2. Doc 02 UHV: empty-name subject restored print-anchored from the doc header
   ('KVE301/ KVE 401/ KVE 301H/ KVE 401 H Universal Human Values and Professional
   Ethics'); objectives + units via ONE mercury-3 REX call (B44 REX class).
3. Doc 06 (mca_syllabus, 1-page scan, empty text layer): hand draft created by
   the run agent from the page-image render (RULES §6), flagged
   unit_ocr_recovered_no_text_layer with page-citing quirk; MCA-211 (course MCA).
"""
import json, re, subprocess, sys

PD = "/home/z/my-project/work/pipeline_v2/parsed"
DR = "/home/z/my-project/work/pipeline_v2/drafts"

def atomic(codes):
    out = []
    for c in codes:
        for part in re.split(r"[/,]", c):
            t = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", part)
            t = re.sub(r"\s+", "", t).strip("-")
            if t and t not in out:
                out.append(t)
    return out

def quirk_add(s, q):
    qs = s.get("quirks") or []
    if q not in qs:
        qs.append(q)
    s["quirks"] = qs

STEMS = ["01_btech_s3-4_kas303-403-maths-iii-integral-transform-discrete",
         "02_btech_s3-4_kve301-401h-universal-human-values-professional-ethics",
         "03_btech_s3-4_roe030-roe040-open-electives-science",
         "05_mba_syllabus"]
for stem in STEMS:
    p = f"{DR}/{stem}.draft.json"
    d = json.load(open(p))
    nch = 0
    for s in d["subjects"]:
        old = list(s.get("codes") or [])
        new = atomic(old)
        if new != old:
            nch += 1
            s["codes"] = new
            s.setdefault("codes_print", " / ".join(old)) if not s.get("codes_print") else None
            quirk_add(s, f"compound/en-dashed code print(s) {', '.join(repr(c) for c in old)} split to "
                         f"atomic codes {new} draft-side for ladder matching; verbatim cell print kept "
                         f"in codes_print (v10 atomic_codes class)")
    json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
    print(f"CODESPLIT|{stem}|changed: {nch}")

# ---- doc 02 UHV restore + REX
P02 = f"{DR}/02_btech_s3-4_kve301-401h-universal-human-values-professional-ethics.draft.json"
d02 = json.load(open(P02))
s = d02["subjects"][0]
s["name"] = "Universal Human Values and Professional Ethics"
s["name_print"] = "Universal Human Values and Professional Ethics"
s["codes"] = ["KVE301", "KVE401", "KVE301H", "KVE401H"]
s.setdefault("codes_print", "KVE301/ KVE 401/ KVE 301H/ KVE 401 H")
s["subject_type"] = "value-added"
s["ltp"] = {"l": 3, "t": 0, "p": 0}
s["credit"] = 3
ft = open(f"{PD}/02_btech_s3-4_kve301-401h-universal-human-values-professional-ethics.fulltext.txt",
          encoding="utf-8").read()
iobj = ft.find("Objectives")
iu1 = re.search(r"Unit[\s-]*1", ft, re.I)
if iobj != -1 and iu1:
    s["objectives_print"] = [ft[iobj:iu1.start()].strip()]
prompt = ("Extract the UNIT text of this AKTU syllabus subject VERBATIM. Return ONLY a JSON object "
          'with keys "units" (mapping "1".."N" to the full verbatim unit text incl. any unit heading) '
          "— no commentary. Keep every word and printed punctuation; do not correct anything.\n\n"
          "SOURCE (full detail pages):\n\n" + ft)
open("/tmp/rex_kve_prompt.txt", "w").write(prompt)
r = subprocess.run([sys.executable, "/home/z/my-project/scripts/pipeline_v2/mercury_call.py",
                    "--prompt-file", "/tmp/rex_kve_prompt.txt",
                    "--max-tokens", "4000", "--temperature", "0.5", "--timeout", "300"],
                   capture_output=True, text=True, timeout=330)
print("REX|KVE301|exit", r.returncode, "|", r.stderr.strip()[:100])
if r.returncode == 0:
    m = re.search(r"\{.*\}", r.stdout.strip(), re.S)
    units = json.loads(m.group(0)).get("units") if m else None
    if units and isinstance(units, dict) and len(units) >= 3:
        s["units"] = {str(k): v for k, v in units.items()}
        quirk_add(s, "units re-extracted via mercury-3 REX from the doc's detail text (B44 REX class); "
                     "extraction row had returned empty")
json.dump(d02, open(P02, "w"), indent=1, ensure_ascii=False)
print("RESTORED|KVE|name + objectives:", len(s.get("objectives_print") or []), "| units:", len(s.get("units") or {}))

# ---- doc 06 hand draft (page-image transcription by the run agent; image read in-conversation)
D06 = {
    "pdf_rel": "repo_asleep/PDFs/5-course/no_session_found/mca_syllabus.pdf",
    "session": "",
    "course": "MCA",
    "sha16": "6934010f5bfcb881",
    "stem": "06_mca_syllabus",
    "subjects": [{
        "name": "Environmental Science and Ethics",
        "name_print": "MCA 211 : Environmental Science & Ethics",
        "codes": ["MCA-211"],
        "codes_print": "MCA 211",
        "semester": None,
        "ltp": None,
        "credit": None,
        "marks": None,
        "subject_type": "core",
        "units": {
            "1": "Knowing our environment, socio-economic, political & environmental situations of India, Population, The land, Forest & wild life, energy sources, Toxic Chemicals & Toxicity, Hazardous waste, sustainability and Human Development.",
            "2": "Ecology, Principles of Energy and Matter in the environment, Food Chain, Carbon and Nitrogen cycles, Biodiversity, benefits and what threatens it, Causes of extinction of the species and their remediation.",
            "3": "Perspectives of global environmental issues, the green house effect, sources of carbon emissions, chlorofluorocarbons, their major uses and combined effect of green house gases, stratosphere, Ozone depletion and impacts.",
            "4": "Environmental Pollution; causes, pollutants their effect and control of pollution – (i) Air (ii) Water (iii) Soil (iv) Noise (v) Thermal (vi) Marine, the legislation of air & water pollution, solid and/ hazardous waste disposal.",
            "5": "Social issues and environment, the western perspective, Environmental ethics, conservation of natural resources, Effectiveness of various religions in environmental conservation, technological progress and quality of life, harmony between materialism and spiritualism, imbibing human values in environmental studies, NGOs and their role in environmental preservations."
        },
        "lectures_per_unit": None,
        "cos": [],
        "textbooks": [
            {"no": 1, "book": "Environmental Studies – Benny Joseph – Tata McGrawHill-2005"},
            {"no": 2, "book": "Environmental Studies – Dr. D.L. Manjunath, Pearson Education-2006."},
            {"no": 3, "book": "Environmental studies – R. Rajagopalan – Oxford Publication - 2005."},
            {"no": 4, "book": "Text book of Environmental Science & Technology – M. Anji Reddy – BS Publication."}
        ],
        "reference_books": [
            {"no": 1, "book": "Principles of Environmental Science, Curnningham. W.P. & Cunningham M.A., Tata McGraw Hill Publishing Co. Ltd., New Delhi."},
            {"no": 2, "book": "India's Environmental Policies, Programmes & Stewardship by Prof. O.P. Dwivedi, Macmilan Press Ltd., London."},
            {"no": 3, "book": "Textbook of Environment & Ecology by Deeksha Dave and S.S. Katewa, Cengage Learning India Pvt. Ltd., Patparganj, Delhi, 2009."},
            {"no": 4, "book": "Principles of Environmental Science and Engineering – P. Venugoplan Rao, Prentice Hall of India."},
            {"no": 5, "book": "Environmental Science & Engineering – Meenakshi, Prentice Hall India."}
        ],
        "experiments": [],
        "objectives_print": [],
        "prerequisites": "",
        "quirks": [
            "subject content transcribed from the page-image render p.1 (1-page scan; text layer empty at 19 chars; RULES §6 visible print authoritative; transcribed by the run agent in-conversation)",
            "printed typos kept verbatim: 'Curnningham', 'Macmilan', 'preservations', 'green house' (two words)"
        ],
        "flags": ["unit_ocr_recovered_no_text_layer"]
    }],
    "non_subject_rows": [],
    "quirks": ["1-page scanned print of the single subject MCA 211; text layer empty; all content page-image transcribed"],
    "flags": ["page-image-transcription-source"]
}
json.dump(D06, open(f"{DR}/06_mca_syllabus.draft.json", "w"), indent=1, ensure_ascii=False)
print("HANDDRAFT|06_mca_syllabus|1 subject (MCA-211, 5 units, 4 tb, 5 rb)")
