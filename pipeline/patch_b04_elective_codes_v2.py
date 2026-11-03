#!/usr/bin/env python3
"""patch_b04_elective_codes_v2.py — precise restoration of printed variant
codes + Bio-similars image transcription.

Lessons recorded from the v1 corruption (reverted by re-running
merge_s04_partials.py from archived partials):
- v1 matched subject names on SCHEME-TABLE pages (every name appears there)
  and stole the first BP token on such pages -> wrong codes. v2 anchors on
  the subject's DETAIL page (contains name + 'course code' + 'course
  objectives'/'detailed syllabus' normalized) and only touches subjects
  whose codes are base-slot codes or empty (slot-stripped variants).
- The 2026-27 print carries DISTINCT variant codes: 'BP607T AEC4' (DSBM,
  p.241 image), 'BP708T AEC6' (Bio-similars, p.270 image).

Bio-similars BP708T AEC6 units transcribed from the VISIBLE print (pp.270-271
images) — the text layer drops bullet lead words (glyph-encoding defect;
e.g. p.271 prints '-PAGE, SEC-HPLC' where the image shows 'Physicochemical:
SDS-PAGE'). RULES §6: visible print is authoritative.
"""
import json, re

P = "/home/z/my-project/work/pipeline_v2/parsed/04_bpharm_scheme-syllabus_2026-27.json"
D = "/home/z/my-project/work/pipeline_v2/drafts/04_bpharm_scheme-syllabus_2026-27.draft.json"

BASE_SLOT_CODES = {"BP212P", "BP312P", "BP607T", "BP610P", "BP611P",
                   "BP708T", "BP806T", "BP809P"}
TOK = re.compile(r"\b(BP\d{3}[TP]\s?(?:AEC|SEC|VAC)\s?\d+)\b")


def norm_al(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


BIOSIM_UNITS = {
    "1": ("Introduction to Biosimilars, Vaccines and Macromolecules • Classes: Monoclonal "
          "antibodies (mAbs), cytokines, insulin, growth factors; primary/secondary/tertiary "
          "structures. • Biosimilars: Definition, rationale, types (e.g.. erythropoietin, "
          "filgrastim). • Vaccines: Generations (live, subunit, viral vector, mRNA); adjuvants "
          "and delivery systems. • Industry landscape: Blockbuster biologics (Humira, "
          "Keytruda), Indian biosimilar market."),
    "2": ("Characterization Methodologies • Physicochemical: SDS-PAGE, SEC-HPLC, peptide "
          "mapping, mass spectrometry. • Glycosylation analysis: N-linked glycans (HILIC, "
          "lectin arrays). • Functional assays: Cell-based potency, binding ELISA, ADCC. • "
          "Comparability for biosimilars: Fingerprinting (ICH Q5E)."),
    "3": ("Manufacturing Protocols • Upstream: Cell line development (CHO, HEK), bioreactors, "
          "media optimization. • Downstream: Harvesting, chromatography (affinity, "
          "ion-exchange), viral clearance. • Fill-finish: Lyophilization, aseptic processing, "
          "cold chain. • Process analytical technology (PAT) in biologics."),
    "4": ("Quality Control and Stability Protocols • Release testing: Host cell proteins "
          "(HCP), DNA, sterility, endotoxin (LAL). • Stability: ICH Q5C for biologics; "
          "subvisible particles, aggregation. • Immunogenicity assessment: ADA assays, "
          "neutralizing antibodies. • Vaccine QC: Potency, identity, safety (animal models)."),
    "5": ("Regulatory Compliances and Case Studies • Global: USFDA 351(k) biosimilar pathway, "
          "EMA guidelines, WHO prequalification. • India: CDSCO Biosimilar Guidelines 2021, "
          "DCGI vaccine approvals. • Documentation: BLA/CMC modules, PK/PD comparability "
          "studies. • Case studies: COVID-19 mRNA vaccines (Pfizer), Indian trastuzumab "
          "biosimilars."),
}
BIOSIM_BOOKS = [
    {"no": 1, "book": "Genomic and Precision Medicine by Geoffrey S. Ginsburg & Huntington F. Willard"},
    {"no": 2, "book": "Genomics and Personalized Medicine by Michael Snyder"},
    {"no": 3, "book": "Deep Medicine by Eric Topol"},
]


def main():
    rec = json.load(open(P))
    pages = [p["text"] for p in rec["pages"]]
    npages = [norm_al(t) for t in pages]
    d = json.load(open(D))
    patched, unresolved = [], []
    for s in d["subjects"]:
        cur = s.get("codes", [])
        base = {re.sub(r"[^A-Z0-9]", "", c.upper()) for c in cur}
        is_target = (not cur) or (base & {re.sub(r"[^A-Z0-9]", "", c) for c in BASE_SLOT_CODES})
        if not is_target:
            continue
        nm = s.get("name", "")
        key = norm_al(nm)[:36]
        detail = None
        for pi, nt in enumerate(npages):
            if key and key in nt and "coursecode" in nt and (
                    "courseobjectives" in nt or "detailedsyllabus" in nt):
                detail = pi
                break
        if detail is None:
            unresolved.append(nm)
            continue
        t = pages[detail]
        m = TOK.search(t)
        if not m:
            unresolved.append(nm + " (no suffixed token)")
            continue
        printed = re.sub(r"\s+", " ", m.group(1))
        s["codes"] = [printed]
        s.setdefault("quirks", []).append(
            f"variant code restored to printed token '{printed}' (p.{detail+1} detail-page Course-Code cell; "
            f"partial-merge had {cur or '[]'})")
        fl = [f for f in (s.get("flags") or [])
              if "SHARED-CODE-ELECTIVE-VARIANT" not in str(f)
              and "variant-code-restored-from-print" not in str(f)]
        s["flags"] = fl
        if "code_note" in s:
            s.setdefault("quirks", []).append("code_note removed — printed code is variant-distinct")
            del s["code_note"]
        q = [x for x in (s.get("quirks") or [])
             if "code ownership assigned to the first printed variant" not in x]
        s["quirks"] = q
        patched.append((nm[:44], cur, printed, detail + 1))
    # ---- Bio-similars image transcription ----
    bs = next((s for s in d["subjects"] if s.get("name", "").startswith("Bio-similars")), None)
    bs_done = False
    if bs:
        bs["units"] = dict(BIOSIM_UNITS)
        bs["reference_books"] = BIOSIM_BOOKS
        bs["codes"] = ["BP708T AEC6"]
        fl = [f for f in (bs.get("flags") or [])
              if "NEEDS-REVIEW-UNIT-TEXT-IMAGE-EMBEDDED" not in f]
        fl.append("unit-text-glyph-defect-transcribed-from-page-image-pp.270-271")
        bs["flags"] = fl
        bs.setdefault("quirks", []).append(
            "text layer drops bullet lead words (glyph-encoding defect; p.271 extracts "
            "'-PAGE, SEC-HPLC' where the print reads 'Physicochemical: SDS-PAGE'); units "
            "transcribed from the visible page images pp.270-271 per RULES §6")
        bs_done = True
    d.setdefault("quirks", []).append(
        "pipeline note: elective variant codes restored from detail-page Course-Code cells "
        "(BPxxxT/P AEC/SEC/VAC n; images pp.241/270); Bio-similars BP708T AEC6 units "
        "transcribed from page images pp.270-271 (glyph-encoding defect in text layer)")
    json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
    print(f"PATCHED|{len(patched)}|biosimilars={bs_done}|UNRESOLVED|{len(unresolved)}")
    for nm, cur, new, pg in patched:
        print(f"CODE|{nm}|{cur}->{new}|p{pg}")
    for nm in unresolved:
        print(f"UNRESOLVED|{nm[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
