# units_compat.py — shape adapter for the units field across draft eras.
#
# EVIDENCE (recorded 2026-10-28, CRON-20261028-B03): two draft eras coexist in
# work/pipeline_v2/drafts:
#   (a) RULES §7 shape — units is a DICT {"1": "<verbatim text>", ...} (has sha16,
#       non_subject_rows); produced by the per-subagent draft flow.
#   (b) segmentation-flow shape — units is a LIST of dicts
#       {no, title_print, text_verbatim[, weightage_print, lectures_print,
#       hours_print, no_print]}; produced by make_b03_segments/fragment builders.
# The B02-era merge/verify tools assume (a). This adapter converts (b) -> (a)
# WITHOUT inventing content: unit text = element's text_verbatim verbatim; the
# extra per-unit print metadata has no registry column (G1 forbids adding one),
# so a quirk note is recorded on the subject naming exactly which units carried
# which extra print fields. Raw drafts on disk remain the full-fidelity source.
# Zero content is dropped silently; containment checks run on text_verbatim.

EXTRA_KEYS = ("title_print", "weightage_print", "lectures_print", "hours_print", "no_print")


def normalize_draft_units(d):
    """Mutate draft dict in place: list-form units -> dict-form. Idempotent."""
    changed = 0
    for s in d.get("subjects") or []:
        u = s.get("units")
        if isinstance(u, list):
            out, extras = {}, []
            for el in u:
                if not isinstance(el, dict):
                    continue
                no = str(el.get("no", "")).strip()
                txt = el.get("text_verbatim")
                if txt is None:
                    txt = el.get("text", "")
                if no:
                    out[no] = txt or ""
                present = [k for k in EXTRA_KEYS if el.get(k) not in (None, "")]
                if present:
                    extras.append(f"u{no}:{'+'.join(present)}")
            s["units"] = out
            if extras:
                q = ("units-shape-adapter: segmentation-flow draft; per-unit print metadata "
                     "retained in raw draft only (no unit-level registry column): " + "; ".join(extras))
                if q not in (s.get("quirks") or []):
                    s.setdefault("quirks", []).append(q)
            changed += 1
    return changed
