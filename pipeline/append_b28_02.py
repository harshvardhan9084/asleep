import json, sys, os
DRAFT = "/home/z/my-project/work/pipeline_v2/drafts/28_02_btech_it_syllabus_2016-17.draft.json"
HDR = {"pdf_rel": "repo_asleep/PDFs/5-course/2016-17/btech_it_syllabus_2016-17.pdf",
       "session": "2016-17", "course": "BTech", "sha16": "3f83735be23e91f4",
       "stem": "28_02_btech_it_syllabus_2016-17"}
def load():
    if os.path.exists(DRAFT):
        return json.load(open(DRAFT, encoding="utf-8"))
    d = dict(HDR); d["subjects"] = []; d["non_subject_rows"] = []; d["quirks"] = []; d["flags"] = []
    return d
def save(d):
    json.dump(d, open(DRAFT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def append_subject(s):
    d = load(); d["subjects"].append(s); save(d); print("subjects:", len(d["subjects"]), "-", s["name"])
def append_nonsubject(r):
    d = load(); d["non_subject_rows"].append(r); save(d); print("non_subject_rows:", len(d["non_subject_rows"]))
def extend_quirks(qs):
    d = load(); d["quirks"].extend(qs); save(d); print("quirks:", len(d["quirks"]))
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "init":
        save(load()); print("init ok")
    else:
        payload = json.load(sys.stdin)
        if cmd == "subject": append_subject(payload)
        elif cmd == "nonsubject": append_nonsubject(payload)
        elif cmd == "quirks": extend_quirks(payload)
