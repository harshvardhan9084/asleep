#!/usr/bin/env python3
"""t3_quality_probe.py — quality-test cascade T3 (owner plan 2026-11-11), batch CRON-20261112-B83.

T3 = code-name mismatch (P2, expected yield: low single digits, high buyer value).
  Stage 1: code family (AKTU era grammar + MBA specialization suffix) vs
           subject_name domain. Rule table is CORPUS-DERIVED (per-course family
           dominant-domain histogram over keyword-classified names), not
           hand-guessed: a family is "established" for domain D when its
           detectable-domain rows are concentrated on D (n>=10 family rows,
           >=8 detectable, D share>=0.70). Cross-checked against AKTU
           letter-grammar (recorded in the ledger, secondary).
  Stage 2: for hits ONLY, page-check the row's OWN cited scheme/syllabus line
           (fitz text layer): the name printed WITH the primary code decides.
           print agrees  -> attested grammar-breaker / service-course composition
                             (B76 tightness: print wins, ledger note, never a fix);
           print differs -> print-proven mismatch -> fix/retarget candidate per
                             B20/B76 for a LATER multi-confirmed batch.

Stage-1 funnel arms (suppression recorded, never silent):
  A rare-in-family: name domain established elsewhere in the course but rare
    (<=2 rows) in this family, accumulator guard (no domain-family code in
    all_codes|code_history_all), not an elective/NPTEL/audit/GP pool class.
  B MBA spec: family specialization suffix vs topic keywords.
  Suppressed-but-recorded: count>2 secondary-domain clusters (curriculum
    composition classes, e.g. Agri-engg thermodynamics, ME Python labs).

LEDGER-ONLY: writes work/pipeline_v2/probes/t3_probe_ledger.json. No CSV write,
no quality_flags change (standing mechanics: multi-stage confirmation first).
Never invents a value — every candidate carries stored + printed evidence.
"""
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher

CSV_PATH = "/home/z/my-project/download/art_d_final/syllabus_extreme_rich.csv"
PROBE_DIR = "/home/z/my-project/work/pipeline_v2/probes"
REPO = "/home/z/my-project/work/repo_asleep"
RUN_ID = "CRON-20261112-B83"

# ---------------------------------------------------------------- helpers
def squash(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def norm_name(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def code_prefix(pc):
    m = re.match(r"^([A-Za-z]+)", (pc or "").strip())
    return m.group(1).upper() if m else ""

# ---- keyword tables. Matching is WORD-BOUNDED: ' pad ' in ' name '
# (substring matching produced fore'casting'->ME / 'architecture'->ARCH bugs).
GENERIC_KW = [
    "workshop", "lab", "laboratory", "practical", "project", "seminar", "internship",
    "training", "general proficiency", "value added", "universal human", "constitution",
    "indian knowledge", "economics", "law", "communication skill", "soft skill",
    "engineering graphics", "energy", "environment", "disaster", "hackathon",
    "comprehensive", "viva", "mooc", "foreign language", "german", "french",
    "japanese", "sanskrit", "english", "self study", "mandatory", "induction program",
    "design thinking", "emotional intelligence", "yoga", "sports", "ncc", "nss",
    "creative", "critical", "open elective", "audit", "essence of", "spiritual",
    "human value", "stress", "aptitude", "reasoning", "engineering mechanics",
    "engineering economics", "engineer in society", "nptel", "elective pool",
    "mini project", "major project", "activity", "biology",
    "good manufacturing practices",
]
DOM_KW = [
    ("CS", ["algorithm", "data structure", "data base", "database", "compiler",
            "operating system", "automata", "theory of computation", "dbms",
            "computer network", "software engineering", "software testing",
            "software project", "programming", "python", "java", "object oriented",
            "web technology", "artificial intelligence", "machine learning",
            "deep learning", "cloud", "cyber security", "cryptography", "data mining",
            "data warehousing", "data analytics", "computer graphics", "image processing",
            "unix", "linux", "information security", "data science", "big data",
            "internet of things", "distributed system", "discrete structure",
            "computational", "computer vision", "blockchain", "digital forensics",
            "mobile application", "computer organization", "computer architecture",
            "service oriented architecture", "iot architecture", "e commerce",
            "electronic commerce", "commerce", "full stack", "virtual reality",
            "management information system", "business intelligence"]),
    ("ME", ["thermodynamic", "heat transfer", "machine design", "theory of machine",
            "manufacturing", "ic engine", "internal combustion", "refrigeration",
            "automobile", "strength of material", "dynamics of machinery", "kinematics",
            "metallurgy", "welding", "mechanical", "vibration", "fluid machinery",
            "turbo", "machining", "mechatronics", "cad", "cam", "machine vision",
            "industrial engineering", "ergonomic", "automotive", "power plant",
            "fluid power", "tool engineering", "additive manufacturing",
            "maintenance engineering", "reliability", "casting", "foundry",
            "metal cutting", "machine tools", "plant layout", "work study",
            "production planning", "operations research",
            "tillage", "tractors"]),
    ("CE", ["concrete", "structural analysis", "surveying", "geotechnical",
            "transportation engineering", "highway", "railway", "bridge",
            "soil mechanic", "water supply", "waste water", "sanitation",
            "estimation and costing", "town planning", "hydraulic", "irrigation",
            "civil", "building planning", "earthquake", "foundation engineering",
            "airport", "tunnel", "dam", "hydrology", "groundwater", "watershed"]),
    ("EE", ["electrical machine", "power system", "switchgear",
            "transmission and distribution", "electrical measurement",
            "utilization of electrical", "electric traction", "high voltage",
            "electrical drives", "transformer", "electrical", "electric",
            "circuit"]),
    ("ECE", ["signal", "communication system", "digital communication", "microwave",
             "antenna", "radar", "television", "vlsi", "electronic device",
             "digital electronics", "electronic", "electromagnetic", "optical fiber",
             "satellite", "wireless", "microprocessor", "microcontroller", "embedded",
             "analog", "electronics", "semiconductor", "instrumentation", "sensors"]),
    ("CHE", ["chemical", "reactor", "mass transfer", "momentum transfer", "petroleum",
             "polymer", "distillation", "stoichiometry", "pulp", "sugar technology",
             "leather", "fertilizer", "process dynamics", "fluidization", "extraction",
             "petrochemical", "plastic"]),
    ("PHAR", ["pharmacology", "pharmacognosy", "medicinal chemistry", "pharmaceutics",
              "drug", "dosage", "formulation", "phytochemistry", "pharmaceutical",
              "biopharmaceutics", "cosmeceutic", "pharmacy", "pharmacokinetic"]),
    ("AGRI", ["agriculture", "agronomy", "horticulture", "crop", "farm machinery",
              "livestock", "poultry", "seed technology", "soil science",
              "agri", "fodder", "land and water"]),
    ("BIO", ["biotechnology", "genetic", "cell biology", "biochemistry", "microbiology",
             "enzyme", "fermentation", "immunology", "bioinformatics",
             "molecular biology", "food technology", "food", "nutrition",
             "bioprocess", "dairy", "biomedical", "metabolomic", "metabolic",
             "biostatistics", "biophysics", "bio"]),
    ("TEXT", ["textile", "fibre", "fiber", "spinning", "weaving", "garment",
              "apparel", "knitting", "fabric", "yarn", "dyes", "carpet", "non woven",
              "nonwoven"]),
    ("MGMT", ["marketing", "financial management", "human resource", "organizational",
              "business", "entrepreneurship", "strategic", "corporate", "accounting",
              "retail", "leadership", "management", "managerial", "banking",
              "insurance", "taxation", "investment", "supply chain", "logistics",
              "hrm", "industrial management", "waste management", "safety",
              "hazards", "innovation", "sociology", "ethos"]),
    ("HOTEL", ["hotel", "food production", "front office", "housekeeping", "bakery",
               "tourism", "catering", "hospitality", "travel"]),
    ("MATH", ["mathematics", "mathematical", "physics", "statistics", "probability",
              "numerical", "applied science"]),
]
# MBA specialization suffix -> strong topic keywords
MBA_SPEC_KW = {
    "MK": ["marketing", "brand", "consumer", "advertising", "retail", "sales", "market research"],
    "FM": ["financ", "banking", "investment", "capital", "tax", "portfolio", "insurance"],
    "HR": ["human resource", "hrm", "industrial relation", "labour", "talent", "compensation"],
    "IB": ["international business", "export", "import", "forex", "global"],
    "IT": ["information", "e business", "erp", "business analytics", "management information"],
    "OM": ["operation", "production", "logistic", "supply chain", "quality management"],
    "RD": ["rural"],
    "TC": ["tourism", "travel", "hospitality"],
    "TT": ["tourism", "travel", "hospitality"],
    "HC": ["hospital", "healthcare", "health care"],
    "CM": ["construction", "material"],
    "LS": ["leadership", "labour welfare", "social"],
}
# elective/pool/audit families: every domain is by-design legitimate
POOL_FAMS = {"BOE", "KOE", "ROE", "EOE", "NOE", "OE", "EAU", "KAU", "RAU", "NAU",
             "BAU", "AU", "NGP", "AGP", "GP", "VAC", "BVA", "NONCREDIT", "AUC",
             "ETAU", "O"}
# hand grammar (secondary cross-check, recorded in ledger)
GRAMMAR = {
    "CS": {"CS", "IT", "CAI", "AID", "AI", "CDS", "DS", "BCS", "BCC", "BCAI", "BCAM",
           "BCDS", "BCIT", "BCCS", "AAI", "AID", "ACS", "RCAI", "KCS", "KIT", "KAI",
           "NCS", "NIT", "NIC", "RCS", "RIT", "MCA", "NMCA", "KCA", "BMC", "RCA",
           "NBC", "BMI", "BIC", "KIC", "EIC", "RIC", "KAI", "KDS", "BADS", "BDS"},
    "ME": {"ME", "EME", "NME", "KME", "RME", "AME", "BME", "RBM", "KML", "BMN", "EMT",
           "RMI", "BPI", "NPI", "RPI", "KPI", "EPI", "KPE", "RPE", "BPE", "NPE", "EPL",
           "RPL", "KOT", "MN"},
    "CE": {"CE", "NCE", "KCE", "RCE", "BCE", "ACE", "ECE"},
    "EE": {"EE", "EEE", "EEV", "EEC", "NEE", "KEE", "KEN", "BEN", "REN", "NEN", "REE",
           "BEE", "AEE", "EEN", "REV"},
    "ECE": {"ECT", "ECE", "NEC", "KEC", "REC", "BEC", "AEC", "ECY", "BCY", "BCBS",
            "ECF", "ETC", "ETE", "ETEF", "EI", "EIC"},
    "CHE": {"CH", "ECH", "NCH", "RCH", "KCH", "BCH", "EC", "KWS"},
    "PHAR": {"BP", "RPH", "BOP", "PCA", "RCA", "RVE", "BOP"},
    "AGRI": {"AG", "EAG", "NAG", "KAG", "RAG", "BAG", "KAE", "RAE", "BAE", "NAE",
             "BAI", "KAD", "BVE", "BVL", "RVE"},
    "TEXT": {"TT", "KTT", "ETT", "RTT", "BTT", "TBT", "RCT", "ECT", "KHT", "BHT",
             "EACT", "EHTT", "ETDT", "RTC", "BCT", "KCT"},
    "BIO": {"BT", "EBT", "NBT", "RBT", "BBT", "KBT", "BFT", "EFT", "NFT", "RFT",
            "KFT", "BBI", "ETDT", "BMN"},
    "MGMT": {"MB", "KMB", "BMB", "RMB", "NMB", "MBA", "BMN", "KMBN", "KMT", "RMT",
             "KMTT", "MBTM", "FM", "MK", "KMBA", "KBMA", "BMBA", "KMHC", "BMLS",
             "KMLS", "KMBF", "BMBF", "NONCREDIT"},
    "HOTEL": {"HT", "KHT", "BHT"},
}

def classify_name(name):
    """returns (dom, matched_kw): 'none' | 'generic' | 'multi:..' | DOMAIN."""
    n = " " + norm_name(name) + " "
    if not n.strip():
        return ("none", "")
    for kw in GENERIC_KW:
        if f" {kw} " in n or (kw in n and kw in {"lab", "nptel", "elective pool"}):
            return ("generic", kw)
    hits = []
    for dom, kws in DOM_KW:
        for kw in kws:
            if f" {kw} " in n or f" {kw} " in (" " + n):
                hits.append((dom, kw))
                break
    if len(hits) == 1:
        return hits[0]
    doms = {d for d, _ in hits}
    if len(doms) > 1:
        return ("multi:" + ",".join(sorted(doms)), ";".join(k for _, k in hits))
    return ("none", "")

def mba_spec(fam):
    m = re.search(r"(MK|FM|HR|IB|IT|OM|RD|TC|TT|HC|CM|LS)$", fam)
    return m.group(1) if m else ""

# ------------------------------------------------- corpus rule table
def build_family_table(rows):
    tab = defaultdict(Counter)
    for r in rows:
        f = code_prefix(r["primary_code"])
        if not f or f == "O":
            continue
        dom, _ = classify_name(r["subject_name"])
        if dom.startswith("multi:"):
            dom = "multi"
        tab[(r["course_name"], f)][dom] += 1
    return tab

def established(tab_entry):
    n = sum(tab_entry.values())
    det = {d: c for d, c in tab_entry.items() if d not in ("none", "generic", "multi")}
    ndet = sum(det.values())
    if n < 10 or ndet < 8:
        return None
    dom, cnt = Counter(det).most_common(1)[0]
    return dom if cnt / ndet >= 0.70 else None

# ------------------------------------------------- stage 2 page check
def sha_index():
    idx = {}
    for base, dirs, files in os.walk(REPO):
        parts = base.split(os.sep)
        if "other_courses" in parts:
            dirs[:] = []
            continue
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            p = os.path.join(base, fn)
            try:
                h = hashlib.md5(open(p, "rb").read()).hexdigest()[:16]
                idx[h] = p
            except OSError:
                pass
    return idx

def cite_docs(field):
    out = []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)", field or ""):
        pg = [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]
        out.append((m.group(2), pg))
    return out

def code_regex(code):
    parts = [re.escape(ch) for ch in re.sub(r"[^A-Za-z0-9]", "", code)]
    if not parts:
        return None
    return re.compile(r"[-\s.:()]*".join(parts), re.IGNORECASE)


STOPW = {"and", "of", "the", "for", "in", "i", "ii", "iii", "iv", "v", "lab",
         "practical", "theory", "a", "its", "with"}


def name_near(stored_norm, lines, i):
    """token-prefix match of the stored name within a +/- window of the code line
    (handles wrapped names, abbreviation prints, DE-pool range tables)."""
    win = " ".join(lines[max(0, i - 1):i + 6]).lower()
    wt = {t for t in re.split(r"[^a-z0-9]+", win) if len(t) >= 4}
    st = [t for t in stored_norm.split() if t not in STOPW and len(t) >= 3]
    if not st:
        return False
    hit = sum(1 for t in st
              if any(w.startswith(t[:4]) or t.startswith(w[:4]) for w in wt))
    return hit / len(st) >= 0.6 or (hit >= 2 and len(st) <= 3)


def locate_code(pdf, code_re, pages, stored_norm):
    """(verdict, page, printed_ctx). Cited pages first; if the citation carries
    no page numbers (pp.as-drafted class), scan the WHOLE cited doc — same
    own-doc evidence method as the T1 page-evidence pass. Range-header lines
    (2+ codes, e.g. '(KAG 055- KAG 059)') only count when the stored name sits
    in the adjacent window (DE-pool tables print the names row-wise)."""
    import fitz
    doc = fitz.open(pdf)
    n = doc.page_count
    scan = [p for p in pages if 1 <= p <= n] or list(range(1, n + 1))
    for pg in scan:
        lines = [l.strip() for l in doc[pg - 1].get_text("text").splitlines() if l.strip()]
        for i, l in enumerate(lines):
            if not code_re.search(l.replace(" ", "")):
                continue
            n_codes = len({m.group(0) for m in re.finditer(r"[A-Z]{2,4}[-\s]?\d{2,4}", l.upper())})
            if n_codes >= 2 and not name_near(stored_norm, lines, i):
                continue  # range/table header line, name not adjacent
            ctx = l
            for j in range(i + 1, min(i + 4, len(lines))):
                ctx += " || " + lines[j]
            return ("found", pg, ctx[:320], pages)
    return ("code_not_in_doc", None, "", pages)

def printed_name_near_code(pdf, page, code_re):
    import fitz
    doc = fitz.open(pdf)
    if page - 1 >= doc.page_count:
        return ("page_out_of_range", "")
    lines = [l.strip() for l in doc[page - 1].get_text("text").splitlines() if l.strip()]
    for i, l in enumerate(lines):
        if code_re.search(l.replace(" ", "")) or code_re.search(l):
            ctx = l
            if i + 1 < len(lines) and len(lines[i + 1]) > 3:
                ctx += " || " + lines[i + 1]
            return ("found", ctx[:300])
    return ("code_not_on_page", "")

def page_check(c, idx):
    ev = []
    for field_name in ("cites_scheme", "cites_syllabus"):
        for sha, pages in c[field_name]:
            pdf = idx.get(sha)
            if not pdf:
                ev.append({"src": field_name, "sha16": sha, "verdict": "doc_unresolvable"})
                continue
            v, pg, ctx, cited = locate_code(pdf, code_regex(c["primary_code"]),
                                            pages, norm_name(c["subject_name"]))
            ev.append({"src": field_name, "sha16": sha, "cited_pages": cited,
                       "found_page": pg, "verdict": v, "print": ctx})
            if v == "found":
                return ev
    return ev

# ---------------------------------------------------------------- main
def main():
    os.makedirs(PROBE_DIR, exist_ok=True)
    rows = [r for r in csv.DictReader(open(CSV_PATH)) if r.get("row_kind") == "subject"]
    md5 = hashlib.md5(open(CSV_PATH, "rb").read()).hexdigest()

    tab = build_family_table(rows)
    est = {k: established(v) for k, v in tab.items()}
    est_doms = {d for d in est.values() if d}

    TECH = {"CS", "ME", "CE", "EE", "ECE", "CHE", "PHAR", "AGRI", "BIO", "TEXT"}
    candidates, suppressed = [], Counter()
    clusters = defaultdict(list)
    for r in rows:
        f = code_prefix(r["primary_code"])
        course = r["course_name"]
        if not f:
            suppressed["no_primary_code"] += 1
            continue
        if f == "O":
            suppressed["unresolvable_family_O"] += 1
            continue
        if f in POOL_FAMS:
            suppressed["pool_family"] += 1
            continue
        name_dom, kw = classify_name(r["subject_name"])
        if name_dom in ("generic", "none") or name_dom.startswith("multi:"):
            suppressed[f"name_{name_dom.split(':')[0]}"] += 1
            continue
        famdom = est.get((course, f))
        if name_dom == famdom:
            continue
        famn = sum(tab[(course, f)].values()) if (course, f) in tab else 0
        if famn < 4:
            suppressed["family_tiny"] += 1
            continue
        famcount = tab[(course, f)].get(name_dom, 0)
        if famcount > 2:
            clusters[f"{course}|{f}:name_dom={name_dom}x{famcount}"].append(r["subject_id"])
            suppressed["secondary_domain_cluster"] += 1
            continue
        # arm A: branch-technical domain, rare in family, established elsewhere,
        # accumulator guard. Service domains (MATH/MGMT/HOTEL) are universal
        # curriculum components — never arm-A mismatch candidates.
        if name_dom in TECH and name_dom in est_doms:
            dom_fams = {f2 for (c2, f2), d in est.items() if c2 == course and d == name_dom}
            dom_fams |= GRAMMAR.get(name_dom, set())
            codes = {code_prefix(t) for fl in (r["all_codes"], r["code_history_all"])
                     for t in re.split(r"[;,]", fl or "") if code_prefix(t)}
            if codes & dom_fams:
                suppressed["accumulator_has_domain_code"] += 1
                continue
            candidates.append(mk_cand(r, f, famdom or f"(small n={famn})", name_dom, kw, "armA-rare-technical-domain"))
            continue
        # arm B: MBA specialization mismatch
        if course == "MBA":
            spec = mba_spec(f)
            if spec and spec in MBA_SPEC_KW:
                verdict = spec_verdict(r["subject_name"], spec)
                if verdict:
                    candidates.append(mk_cand(r, f, f"MBA-spec-{spec}", "MGMT", kw, f"armB-{verdict}"))
                    continue
        suppressed["not_established_domain"] += 1

    idx = sha_index()
    stage2 = []
    for c in candidates:
        s2 = dict(c)
        ev = page_check(c, idx)
        s2["page_evidence"] = ev
        found = [e for e in ev if e["verdict"] == "found"]
        if found:
            s2["verdict"] = "print_agrees_attested"
            s2["as_drafted_citation"] = not bool(found[0]["cited_pages"])
        elif any(e["verdict"] == "doc_unresolvable" for e in ev):
            s2["verdict"] = "inconclusive_doc_unresolved"
        elif ev:
            s2["verdict"] = "code_not_in_any_cited_doc"
        else:
            s2["verdict"] = "no_citation"
        stage2.append(s2)

    ledger = {
        "test_id": "T3", "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "csv_md5": md5, "rows_scanned": len(rows),
        "families_established": {f"{c}|{f}": d for (c, f), d in sorted(est.items()) if d},
        "families_total": len(tab),
        "grammar_crosscheck": {d: sorted(v) for d, v in sorted(GRAMMAR.items())},
        "stage1_skip_reasons": dict(suppressed),
        "secondary_domain_clusters_recorded": {k: v[:8] for k, v in sorted(clusters.items())},
        "stage1_candidates": len(candidates),
        "stage2_verdict_counts": dict(Counter(s["verdict"] for s in stage2)),
        "candidates_stage2": stage2,
        "note": ("ledger-only. established = corpus-derived (family n>=10, detectable>=8, "
                 "share>=0.70); word-bounded keyword matching (fore'casting' bug fixed); "
                 "pool/audit/GP families out of scope by design; service domains "
                 "(MATH/MGMT/HOTEL) are universal curriculum components, never arm-A; "
                 "stage-2 = name-near-code window match on the row's OWN cited docs "
                 "(cited pages first, whole-doc fallback for pp.as-drafted citations; "
                 "range-header lines only via adjacent-name rule); print wins per 6b/B76 — "
                 "print_agrees rows are recorded composition/attested classes; rows whose "
                 "cited docs never print the code are the mis-attribution review set."),
    }
    with open(f"{PROBE_DIR}/t3_probe_ledger.json", "w") as fh:
        json.dump(ledger, fh, indent=1)

    print(f"T3 stage1: {len(candidates)} candidates from {len(rows)} rows "
          f"({len(tab)} families, {sum(1 for v in est.values() if v)} established)")
    print("skips:", dict(suppressed))
    print("stage2 verdicts:", ledger["stage2_verdict_counts"])
    for s in stage2:
        print(f"  - {s['sid']} {s['primary_code']} [{s['family']}] est={s['expected_domain']} "
              f"dom={s['name_domain']} :: {s['subject_name'][:52]} -> {s['verdict']}")

def spec_verdict(name, spec):
    n = " " + norm_name(name) + " "
    for kw in GENERIC_KW:
        if f" {kw} " in n:
            return None
    own = sum(1 for kw in MBA_SPEC_KW[spec] if f" {kw}" in n or f"{kw} " in n)
    other = {}
    for s, kws in MBA_SPEC_KW.items():
        if s == spec:
            continue
        c = sum(1 for kw in kws if f" {kw}" in n or f"{kw} " in n)
        if c:
            other[s] = c
    if own >= 1 and not other:
        return None
    if other and own == 0:
        best = max(other, key=other.get)
        return f"name matches spec {best}, family suffix {spec}"
    return None

def mk_cand(r, fam, est_dom, name_dom, kw, extra):
    cs, sy = [], []
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_scheme_line"] or ""):
        cs.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]))
    for m in re.finditer(r"([A-Za-z0-9_.\- ]+\.pdf)#([0-9a-f]{16})([^;]*)",
                         r["source_syllabus"] or ""):
        sy.append((m.group(2), [int(x) for x in re.findall(r"p{1,2}\.(\d+)", m.group(3))]))
    return {"sid": r["subject_id"], "course": r["course_name"],
            "primary_code": r["primary_code"], "family": fam,
            "expected_domain": est_dom, "name_domain": name_dom, "name_kw": kw,
            "subject_name": r["subject_name"], "subject_name_print": r["subject_name_print"],
            "all_codes": r["all_codes"], "code_history_all": r["code_history_all"],
            "effective_session_latest": r["effective_session_latest"],
            "extra": extra, "cites_scheme": cs, "cites_syllabus": sy}

if __name__ == "__main__":
    main()
