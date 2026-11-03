#!/usr/bin/env python3
"""Apply B04 verify remedies: patch draft 04 with PAGE-IMAGE transcriptions
(RULES §6 visible print authoritative) where the PyMuPDF text layer dropped
content. Evidence recorded per fix in quirks."""
import json, sys

DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/batch04_run/04_bpharm_scheme-syllabus_2026-27.draft.json"
NOTES = "/home/z/my-project/work/pipeline_v2/tmp/fixnotes_04.json"

def main():
    draft = json.load(open(DRAFT))
    notes = json.load(open(NOTES))
    dqu = draft.setdefault("quirks", [])
    for fix in notes["fixes"]:
        tgt = None
        for s in draft["subjects"]:
            if s.get("name") == fix["subject_name"]:
                tgt = s
                break
        if tgt is None:
            print(f"PATCH|SKIP|subject not found: {fix['subject_name']}")
            continue
        tgt.setdefault("units", {}).update(fix["units"])
        if fix.get("references"):
            tgt["reference_books"] = fix["references"]
        ev = (f"text layer dropped/mangled unit content for this subject (pp.print 265-266); "
              f"units transcribed from PAGE IMAGE (visible print authoritative, RULES §6) by orchestrator "
              f"({fix.get('code_print','')}); fix recorded {notes['evidence_note'][:80]}")
        tgt.setdefault("quirks", []).append(ev)
        dqu.append(f"{fix['subject_name']}: units re-transcribed from page image (text-layer loss, RULES §6)")
        print(f"PATCH|OK|{fix['subject_name']}|units={sorted(fix['units'])}")
    json.dump(draft, open(DRAFT, "w"), indent=1, ensure_ascii=False)
    print("saved", DRAFT)

if __name__ == "__main__":
    sys.exit(main())
