#!/usr/bin/env python3
"""patch_b25_verify_flags.py — remedies for the 2 verify FAILs (recorded classes):
1. doc01 EEC-609 'Analog & Digital Communication': the print is a RULED TABLE
   (Unit No. | Topic Name | Text Book Nos | Chapter Nos | Page Nos | No. of Lectures).
   The draft had interleaved [TB|Ch|Pages|Lectures] annotations inline, breaking
   unit containment (0.80/0.79). Remedy: units = verbatim Topic-Name runs (line
   wraps joined); table mapping moved to structured `lecture_plan` per unit.
   Page-image cross-check: table print confirmed on pp.31-32 (text layer == print).
2. doc01 (7) + doc10 (4) scheme-row-only subjects (no detailed syllabus printed):
   add flag `scheme_row_only_detailed_syllabus_not_printed` + evidence quirk —
   recorded B23/B24 class.
"""
import json

B25 = "/home/z/my-project/work/pipeline_v2/drafts/B25"

# ---------- doc01 ----------
p1 = f"{B25}/01_btech_en_syllabus_2009-10.draft.json"
d1 = json.load(open(p1))
for s in d1["subjects"]:
    if s["name"] == "Analog & Digital Communication":
        s["units"] = {
 "1": "Elements of communication system and its limitations Amplitude Modulation: Amplitude modulation and detection, Generation and detection of DSB-SC, SSB and vestigial side band modulation, carrier acquisition AM transmitters and receivers, super hetrodyne receiver, IF amplifiers, AGC circuits Frequency Division multiplexing",
 "2": "Angle Modulation: Basic definitions Narrow band and wideband frequency modulation, transmission bandwidth of FM signals Generation and detection of frequency modulation Noise : External noise, internal noise Noise calculations, signal to noise ratio Noise in AM and FM systems",
 "3": "Pulse Modulation: Introduction, sampling process Analog Pulse Modulation Systems-Pulse Amplitude Modulation, Pulse width modulation and Pulse Position Modulation. Waveform coding Techniques: Discretization in time and amplitude, Quantization process, quantization noise, Pulse code Modulation, Differential Pulse code Modulation, Delta Modulation and Adaptive Delta Modulation.",
 "4": "Digital Modulation Techniques: Types of digital modulation, waveforms for amplitude, frequency and phase shift keying, methods of generation of coherent and non-coherent, ASK,FSK and PSK, comparison of above digital techniques.",
 "5": "Time Division Multiplexing: Fundamentals, Electronic Commutator, Bit/byte interleaving, TI carrier system, synchronization and signaling of TI, TDM and PCM hierarchy, synchronization techniques Introduction to Information Theory: Measure of information, Entropy & Information rate, channel capacity, Hartley Shannan law, Huffman coding, shannan Fano coding.",
        }
        s["lecture_plan"] = {
 "print_form": "ruled table: Unit No. | Topic Name | Text Book Nos | Chapter Nos | Page Nos | No. of Lectures (pp.31-32)",
 "1": [
   {"topic": "Elements of communication system and its limitations", "tb": "1", "ch": "1", "pages": "1-10", "lectures": "4"},
   {"topic": "Amplitude Modulation: Amplitude modulation and detection, Generation and detection of DSB-SC, SSB and vestigial side band modulation, carrier acquisition", "tb": "1", "ch": "2", "pages": "90-92, 93-101", "lectures": "4, 2"},
   {"topic": "AM transmitters and receivers, super hetrodyne receiver, IF amplifiers, AGC circuits", "tb": "2", "ch": "3,6", "pages": "43-52, 120-144", "lectures": "4, 4"},
   {"topic": "Frequency Division multiplexing", "tb": "2", "ch": "15", "pages": "564-566", "lectures": "1"},
 ],
 "2": [
   {"topic": "Angle Modulation: Basic definitions", "tb": "1", "ch": "2", "pages": "107-109", "lectures": "1"},
   {"topic": "Narrow band and wideband frequency modulation, transmission bandwidth of FM signals", "tb": "1", "ch": "2", "pages": "109-119", "lectures": "2"},
   {"topic": "Generation and detection of frequency modulation", "tb": "1", "ch": "2", "pages": "120-124", "lectures": "2"},
   {"topic": "Noise : External noise, internal noise", "tb": "2", "ch": "2", "pages": "15-25", "lectures": "2"},
   {"topic": "Noise calculations, signal to noise ratio", "tb": "1", "ch": "2", "pages": "132-147", "lectures": "2"},
   {"topic": "Noise in AM and FM systems", "tb": "", "ch": "", "pages": "", "lectures": ""},
 ],
 "3": [
   {"topic": "Pulse Modulation: Introduction, sampling process Analog Pulse Modulation Systems-Pulse Amplitude Modulation, Pulse width modulation and Pulse Position Modulation.", "tb": "1", "ch": "3", "pages": "183-193", "lectures": "3"},
   {"topic": "Waveform coding Techniques: Discretization in time and amplitude, Quantization process, quantization noise, Pulse code Modulation, Differential Pulse code Modulation, Delta Modulation and Adaptive Delta Modulation.", "tb": "1", "ch": "3", "pages": "193-208, 218-233", "lectures": "5, 4"},
 ],
 "4": [
   {"topic": "Digital Modulation Techniques: Types of digital modulation, waveforms for amplitude, frequency and phase shift keying, methods of generation of coherent and non-coherent, ASK,FSK and PSK, comparison of above digital techniques.", "tb": "3", "ch": "5", "pages": "172-215", "lectures": "7"},
 ],
 "5": [
   {"topic": "Time Division Multiplexing: Fundamentals, Electronic Commutator, Bit/byte interleaving, TI carrier system, synchronization and signaling of TI, TDM and PCM hierarchy, synchronization techniques", "tb": "1", "ch": "3", "pages": "211-217", "lectures": "4"},
   {"topic": "Introduction to Information Theory: Measure of information, Entropy & Information rate, channel capacity, Hartley Shannan law, Huffman coding, shannan Fano coding.", "tb": "1", "ch": "9", "pages": "568-575, 578-580, 587-589", "lectures": "3"},
 ],
        }
        q = s.setdefault("quirks", [])
        q.append("detailed syllabus prints as a ruled lecture-plan table (Unit|Topic|TB|Ch|Pages|Lectures); "
                 "unit texts transcribed from the Topic-Name column (line wraps joined); the TB/Ch/Pages/"
                 "Lectures mapping kept verbatim in lecture_plan (print quirks: 'super hetrodyne', "
                 "'Shannan' x2, 'hierarchy, synchronization techniques')")
        break
for s in d1["subjects"]:
    if not s.get("units") and not s.get("experiments"):
        f = s.setdefault("flags", [])
        if "scheme_row_only_detailed_syllabus_not_printed" not in f:
            f.append("scheme_row_only_detailed_syllabus_not_printed")
        q = s.setdefault("quirks", [])
        ev = f"scheme-row-only evidence: {s.get('quirks',[''])[0] if s.get('quirks') else 'scheme table row only'}"
        if not any("scheme-row-only evidence" in x for x in q):
            q.append(ev)
json.dump(d1, open(p1, "w"), indent=1, ensure_ascii=False)

# ---------- doc10 ----------
p10 = f"{B25}/10_btech_env_y4_syllabus-cbcs_2019-20.draft.json"
d10 = json.load(open(p10))
for s in d10["subjects"]:
    if not s.get("units") and not s.get("experiments"):
        f = s.setdefault("flags", [])
        if "scheme_row_only_detailed_syllabus_not_printed" not in f:
            f.append("scheme_row_only_detailed_syllabus_not_printed")
        q = s.setdefault("quirks", [])
        ev = f"scheme-row-only evidence: no detailed-syllabus page printed for {s.get('codes')}; appears only in the printed scheme table"
        if not any("scheme-row-only evidence" in x for x in q):
            q.append(ev)
json.dump(d10, open(p10, "w"), indent=1, ensure_ascii=False)
print("PATCHED doc01 (EEC-609 units+lecture_plan, 7 scheme-only flags) + doc10 (4 scheme-only flags)")
