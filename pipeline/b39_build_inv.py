#!/usr/bin/env python3
"""b39_build_inv.py — hand-built print-anchored inventories for the B39 docs
whose headers the deterministic scanner misses (recorded B38 map-headers
class). Every entry below is anchored to the visible print:

  doc 02 (2022-23 BVA251): p.1 header prints 'BVA251: SPORTS AND YOGA'.
  doc 04 (2019-20 engg-science): p.1 scheme table pairs dual-code slot prints
    KOE031/041..KOE038/048 with subject names; detail sections p.2-13 carry
    the SAME printed names as caps/title-case headers (name-equality mapping,
    zero-guess; codes appear only in the scheme table).
  doc 05 (2021-22 engg-science): p.2 scheme table KOE031/041..KOE039/049
    (line-broken dual-code prints); detail sections p.3-15; p.15 header
    prints 'DIGITAL ELECTRONICS KOE039/KOE049'.
  doc 07 (2018-19 non-credit): p.2 'COMPUTER SYSTEM SECURITY', p.3 'PYTHON
    PROGRAMMING' — no codes printed anywhere in the doc (non-credit MOOC
    courses; code-less extraction is the recorded zero-guess class).
  doc 08 (2019-20 technical communication): p.1 header prints
    'Technical Communication (KAS301/401)'.
"""
import json, os

INV = "/home/z/my-project/work/pipeline_v2/inv"
os.makedirs(INV, exist_ok=True)

INVS = {
    "02_btech_y1s2_bva251-sports-and-yoga_2022-23": [
        {"class": "detail", "code_print": "BVA251", "name_print": "SPORTS AND YOGA", "page": 1},
    ],
    "04_btech_y2_engg-science-course_2019-20": [
        {"class": "detail", "code_print": "KOE031/041", "name_print": "Engineering Mechanics", "page": 2},
        {"class": "detail", "code_print": "KOE032/042", "name_print": "Material Science", "page": 3},
        {"class": "detail", "code_print": "KOE033/043", "name_print": "Energy Science & Engineering", "page": 5},
        {"class": "detail", "code_print": "KOE034/044", "name_print": "Sensor & Instrumentation", "page": 6},
        {"class": "detail", "code_print": "KOE035/045", "name_print": "Basics Data Structure & Algorithms", "page": 8},
        {"class": "detail", "code_print": "KOE036/046", "name_print": "Introduction to Soft Computing", "page": 10},
        {"class": "detail", "code_print": "KOE037/047", "name_print": "Analog Electronics Circuits", "page": 12},
        {"class": "detail", "code_print": "KOE038/048", "name_print": "Electronics Engineering", "page": 13},
    ],
    "05_btech_y2_engg-science-course_2021-22": [
        {"class": "detail", "code_print": "KOE031/041", "name_print": "Engineering Mechanics", "page": 3},
        {"class": "detail", "code_print": "KOE032/042", "name_print": "Material Science", "page": 4},
        {"class": "detail", "code_print": "KOE033/043", "name_print": "Energy Science & Engineering", "page": 6},
        {"class": "detail", "code_print": "KOE034/044", "name_print": "Sensor & Instrumentation", "page": 7},
        {"class": "detail", "code_print": "KOE035/045", "name_print": "Basics Data Structure & Algorithms", "page": 9},
        {"class": "detail", "code_print": "KOE036/046", "name_print": "Introduction to Soft Computing", "page": 11},
        {"class": "detail", "code_print": "KOE037/047", "name_print": "Analog Electronics Circuits", "page": 13},
        {"class": "detail", "code_print": "KOE038/048", "name_print": "Electronics Engineering", "page": 14},
        {"class": "detail", "code_print": "KOE039/049", "name_print": "Digital Electronics", "page": 15},
    ],
    "07_btech_y2_non-credit-courses_2018-19": [
        {"class": "detail", "code_print": "", "name_print": "COMPUTER SYSTEM SECURITY", "page": 2},
        {"class": "detail", "code_print": "", "name_print": "PYTHON PROGRAMMING", "page": 3},
    ],
    "08_btech_y2_technical-communication_2019-20": [
        {"class": "detail", "code_print": "KAS301/401", "name_print": "Technical Communication", "page": 1},
    ],
}

for stem, subs in INVS.items():
    json.dump(subs, open(f"{INV}/{stem}.inv.json", "w"), indent=1, ensure_ascii=False)
    print("INV|", stem, "|", len(subs), "detail entries")
