#!/usr/bin/env python3
"""B04 patch: mark AKTU 2026-27 APPENDIX elective-pool subjects with the
'elective-pool-code-slot' flag. Print evidence: p.220 'APPENDIX — List of
Recommended Electives (AEC/SEC/VAC courses to be prescribed by HEI)' prints
ONE code (e.g. BP607T) against SEVERAL candidate course titles, each detailed
later in the appendix — a code slot shared by multiple candidate courses."""
import json

D = "/home/z/my-project/work/pipeline_v2/drafts/batch04_run/04_bpharm_scheme-syllabus_2026-27.draft.json"

def main():
    d = json.load(open(D))
    n = 0
    for s in d["subjects"]:
        codes = s.get("codes") or []
        name = s.get("name", "")
        # pool rows (name carries '(elective pool)') and appendix members of
        # the shared-slot codes
        if ("(elective pool)" in name or "(elective pool)" in s.get("name_print", "")
                or any(c in ("BP212P", "BP312P", "BP607T", "BP610P", "BP611P", "BP708T", "BP806T", "BP809P") for c in codes)):
            fl = s.setdefault("flags", [])
            if not any("elective-pool-code-slot" in f for f in fl):
                fl.append("elective-pool-code-slot (AKTU print: APPENDIX 'List of Recommended Electives (AEC/SEC/VAC)' assigns ONE code to SEVERAL candidate courses — p.220 + per-course appendix sections)")
                n += 1
    json.dump(d, open(D, "w"), indent=1, ensure_ascii=False)
    print("flagged", n, "elective-pool-code-slot subjects")

if __name__ == "__main__":
    main()
