#!/usr/bin/env python3
"""b41_inv_d01.py — deterministic print-anchored inventory for B40 doc 01
(2021-22 OE-III/IV list; mercury inventory failed 3× with junk — the recorded
B39 instability class for list-type docs). Every entry anchored to the visible
detail-header prints (grep-verified page anchors in the parsed fulltext):

  p.2/p.3 print the OE-III list (KOE-080..089) + OE-IV list (KOE-090..099);
  pp.4-13 carry the OE-III detail headers 'KOE0xx: NAME'; pp.15-25 the OE-IV
  detail headers 'KOE09x NAME' (KOE-098's detail header prints 'BAUDDHA AND
  JAIN DARSHAN' while the list prints 'BUDDHA AND JAIN DARSHAN' — print
  variance recorded; KOE-099 prints the combining-Ś form 'VEDIC DARŚANA').
"""
import json, os

INV = "/home/z/my-project/work/pipeline_v2/inv"
os.makedirs(INV, exist_ok=True)

subs = [
    {"class": "detail", "code_print": "KOE080", "name_print": "FUNDAMENTALS OF DRONE TECHNOLOGY (UNMANNED AERIAL VEHICLES)", "page": 4},
    {"class": "detail", "code_print": "KOE081", "name_print": "CLOUD COMPUTING", "page": 5},
    {"class": "detail", "code_print": "KOE082", "name_print": "BIOMEDICAL SIGNAL PROCESSING", "page": 6},
    {"class": "detail", "code_print": "KOE083", "name_print": "ENTREPRENEURSHIP DEVELOPMENT", "page": 7},
    {"class": "detail", "code_print": "KOE084", "name_print": "INTRODUCTION TO SMART GRID", "page": 8},
    {"class": "detail", "code_print": "KOE085", "name_print": "QUALITY MANAGEMENT", "page": 9},
    {"class": "detail", "code_print": "KOE086", "name_print": "INDUSTRIAL OPTIMIZATION TECHNIQUES", "page": 10},
    {"class": "detail", "code_print": "KOE 087", "name_print": "VIROLOGY", "page": 11},
    {"class": "detail", "code_print": "KOE088", "name_print": "NATURAL LANGUAGE PROCESSING", "page": 12},
    {"class": "detail", "code_print": "KOE089", "name_print": "HUMAN VALUES IN MADHYASTH DARSHAN", "page": 13},
    {"class": "detail", "code_print": "KOE090", "name_print": "ELECTRIC VEHICLES", "page": 15},
    {"class": "detail", "code_print": "KOE091", "name_print": "AUTOMATION AND ROBOTICS", "page": 16},
    {"class": "detail", "code_print": "KOE092", "name_print": "COMPUTERIZED PROCESS CONTROL", "page": 17},
    {"class": "detail", "code_print": "KOE093", "name_print": "DATA WAREHOUSING & DATA MINING", "page": 18},
    {"class": "detail", "code_print": "KOE094", "name_print": "DIGITAL AND SOCIAL MEDIA MARKETING", "page": 19},
    {"class": "detail", "code_print": "KOE095", "name_print": "MODELING OF FIELD-EFFECT NANO DEVICES", "page": 20},
    {"class": "detail", "code_print": "KOE096", "name_print": "MODELLING AND SIMULATION OF DYNAMIC SYSTEMS", "page": 21},
    {"class": "detail", "code_print": "KOE097", "name_print": "BIG DATA", "page": 22},
    {"class": "detail", "code_print": "KOE098", "name_print": "HUMAN VALUES IN BAUDDHA AND JAIN DARSHAN", "page": 23},
    {"class": "detail", "code_print": "KOE099", "name_print": "HUMAN VALUES IN VEDIC DARŚANA", "page": 25},
]
json.dump(subs, open(f"{INV}/01_btech_y4s8_open-elective-3-4-list_2021-22.inv.json", "w"), indent=1, ensure_ascii=False)
print("INV|01_btech_y4s8_open-elective-3-4-list_2021-22|", len(subs), "detail entries")
