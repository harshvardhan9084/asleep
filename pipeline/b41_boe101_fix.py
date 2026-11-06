#!/usr/bin/env python3
"""b41_boe101_fix.py — deterministic hand-build for doc 02's BOE101
HUMAN VALUES IN VEDIC DARŚANA (2025-26 OE-IV list, BTech).

Evidence: 3 consecutive mercury-3 extraction attempts (engine run, b37_resume,
direct slice call) returned empty/echo-junk for this subject — the recorded
empty-content class recurring on the combining-diacritic print (DARŚANA/Nyāya/
padārthas...). RULES §6: the visible print is authoritative — pp.41-43 of the
parsed text layer carry the FULL detail (header 'BOE101: HUMAN VALUES IN VEDIC
DARŚANA', L-T-P 3-1-0, units I-V with proposed lectures 09/07/12/08/06, 25
reference books), transcribed here verbatim (line wraps joined). Zero guessing:
only what the print shows.
"""
import json

P = "/home/z/my-project/work/pipeline_v2/drafts/02_btech_y4s8_open-elective-3-4-list_2025-26.draft.json"
d = json.load(open(P))

u1 = ("Introduction to Vedic Darśana and Nyāya Darśana (Philosophy of Indian Logic and Reasoning)\n"
      "Introduction to Vedic literature, need to study Vedic Darśana; its origin and subject matter. "
      "Introduction to Nyāya Darśana, 16 padārthas (pramāṇa, prameya, saṃśaya, prayojana, dṛṣṭānta, siddhānta, "
      "avayava, tarka, nirṇaya, vāda, jalpa, vitaṇḍā, hetuābhāsa, chala, jāti, nigrahasthāna) paṃcāvayava "
      "prakriyā (pratijñā, hetu, udāharaṇa, upanaya, nigamana).")
u2 = ("Vaiśeṣika Darśana (Philosophy of Matter)\n"
      "Introduction to Vaiśeṣika Darśana, definition of Dharma, abhyudaya, niḥśreyasa; 6 padārthas (dravya, "
      "guṇa, karma, sāmānya, viśeśa, samavāya) – their definition, characteristics and relationship; "
      "nitya-anitya; cause-effect relationships; dṛṣṭa-adṛṣṭa karma phala; mindful dāna; śucitā-aśucitā; "
      "reasons of rāga-dveśa, avidyā, sukha-duḥkha, etc. and how to get rid of them.")
u3 = ("Sāṃkhya-Yoga Darśana (Philosophy of Spirituality)\n"
      "Sāṃkhya Darśana- Puruṣārtha, the nature of Puruṣa and Prakṛti, 24 elements of Prakṛti, bondage and "
      "salvation (liberation), the principle of satkāryavāda, triguṇātmaka prakṛti.Yoga Darśana- the steps of "
      "Aṣṭāṃga yoga (yama, niyama, āsana, prāṇāyāma, pratyāhāra, dhāraṇā, dhyāna and samādhi) and the "
      "challenges in following them, afflictions (kleṣa)- avidyā, asmitā, rāga, dveṣa, abhiniveśa, different "
      "types of vṛttis (pramāṇa, viparyaya, vikalpa, nidrā, smṛti), the process of nirodha of vṛttis; maitri, "
      "karuṇā, muditā, upekṣā; description of yama, niyama, āsana and praṇayāma; kriyāyoga– tapa, svādhyāya "
      "and īśvara-praṇidhāna; different steps of samādhi, different types of saṃyama, vivekakhyāti, prajñā.\n"
      "Vedanta Darshan\n"
      "Vedanta Darshan- Nature of Brahma and Prakriti, Methods of Upasana; adhyasaand sanskar; nature of "
      "Atma, description of existence, principle of karma-phala, description o pancha kosha, different nature "
      "of paramatma/brahma, Ishwar, Four qualifications (Sadhan chatushtay).")
u4 = ("Upaniṣad and Vedanta Darśana (Philosophy of God)\n"
      "Introduction to Upaniṣads and Vedanta Darśana; Īśopaniṣad – Idea of renouncement, Karma Yoga, balance "
      "of Vidyā-Avidyā and Prakṛti-Vikṛti; Tattirīyopaniṣad – Different names of the God and their meaning, "
      "parting message of Guru to the graduating student (Śikṣāvallī), Nature of Brahma and Prakṛti, Methods "
      "of Upāsanā; Nature of Ātmā, Description of existence, principle of karma-phala, description of paṃca "
      "kośa, nature of mukti , process and way to achieve it, antaḥkaraṇa-śuddhi, different characteristics "
      "of paramātmā/brahma, Īśvara, Four qualifications (Sādhana-catuṣṭaya)")
u5 = ("Purpose and Program for a Human Being based on the Vedic Darśana\n"
      "The purpose and program of a human being living on the basis of the Vedic Darśana, clarity and "
      "practice of human values and human conduct, the natural outcome of such a program on society, nature "
      "and tradition. Vedic system of living in a society - the idea of vratas and varaṇa (freedom of choice "
      "with commitment), Varṇa System, Āśrama System, Paṃca Mahāyajṇa, 16 Saṃskāras, etc.")

ref = [
    "Acharya Udayveer Shastri, Sankhya Darshanam (vidyodaya Bhashyam), Govindram Hasanand.",
    "Acharya Rajveer Shastri, Patanjal Yog Darśana Bhashyam, Arsha Sahitya Prachar Trust.",
    "Acharya Udayveer Shastri, Brahma Sutra (Vedanta Darshanam), Govindram Hasanand.",
    "Krishna, I. (2010) The SāṃkhyaKarika, BharatiyaVidyaPrakashan, 4th edition",
    "Madhavacharya, Sarva-DarshanaSamgrah Chaukhambha Vidyabhavan, Varanasi.",
    "Muller, F.M. (1928) The Six Systems of Indian Philosophy, London: Longmans Green and Co. Publication.",
    "Maharaj O. () PatanjalYogpradeep, Geeta press Gorakhpur",
    "Vachaspati M. Sankhyatatvakaumudi, Motilal Banarasi Das Publication.",
    "Shreemad Bhagwat geeta",
    "Shankaracharya, VivekChoodamani",
    "Rajyoga, Swami Shivananda",
    "The Nyāya Sutras of Gotama, Sinha, N. (Ed.). Motilal Banarsidass Publ. (1990).",
    "Pandit Madanmohan Vidyasagar. Sanskar Samuchaya, Vijaykumar Govindram Hasanand. 1998",
    "Vedic Vision: Ancient Insights Into Modern Life, Satyavrata Siddhantalankar, Vijay Krishn Lakhanpal, 1999",
    "Sanskar Chandrika (Hindi), Dayananda Saraswati, and Satyavrata Siddhantalankar. Vijay Krishn Lakhanpal, (1990).",
    "THE TAITTIRIYA Upanishad, Achari, Sri Rama Ramanuja. (2013).",
    "Vedic religion: The Taittiriya-Upanishad with the commentaries of Sankaracharya Suresvaracharya and Sayana (Vidyarana). Sastri, A. Mahadeva.(2016).",
    "Taittiriyopanishad Sankara Bhashya With Hindi Translation Gita Press 1936.",
    "Gautama's Nyāyasūtras: With Vātsyāyana-Bhāṣya. Jha, Ganganatha, ed. Oriental Book Agency, 1939.",
    "NyayaDarshnam, Acharya Udayveer Shastri, Vijaykumar Govindram Hasanand (2018)",
    "VaisheeshikaDarshanam, Acharya Udayveer Shastri, Vijaykumar Govindram Hasanand (2017)",
    "Chattejee, S.G. and Datta, D.M. (1960) An Introduction to Indian Philosophy,Calcutta: University of Calcutta Press.",
    "A Foundation Course in Human Values and Profession Ethics (Text Book and Teachers' Manual), R. R. Gaur, R. Asthana, G. P. Bagaria (2019 Second Revised Edition), Excel Books, New Delhi [ISBN 978-93-87034-47-1].",
    "Class notes on \"Human Values in Vedic Darśana\" available on www.uhv.org.in",
    "PPTs for \"Human Values in Vedic Darśana\" available on www.uhv.org.in",
]

obj = {
    "name": "Human Values in Vedic Darśana",
    "name_print": "BOE101: HUMAN VALUES IN VEDIC DARŚANA",
    "codes": ["BOE101"],
    "semester": 8,
    "ltp": {"l": 3, "t": 1, "p": 0},
    "credit": 4,
    "marks": None,
    "subject_type": "open-elective",
    "units": {"1": u1, "2": u2, "3": u3, "4": u4, "5": u5},
    "lectures_per_unit": None,
    "cos": [],
    "textbooks": [],
    "reference_books": [{"no": i + 1, "book": b} for i, b in enumerate(ref)],
    "experiments": [],
    "objectives_print": [],
    "prerequisites": "",
    "quirks": [
        "hand-built from the pp.41-43 print after 3 mercury-3 extraction attempts returned empty "
        "(echo-junk class recurring on the combining-diacritic subject print; b41_boe101_fix.py; "
        "RULES §6 visible-print-authoritative)",
        "unit lectures printed per unit: I=09, II=07, III=12, IV=08, V=06 (Proposed Lecture column)",
        "p.2/p.23 list print carries '**HUMAN VALUES IN VEDIC DARSANA' (ASCII-S form) while the detail "
        "header p.41 prints 'HUMAN VALUES IN VEDIC DARŚANA' (combining-Ś) — same subject, print variance kept",
        "** mandatory-Trained-Faculty note prints for BOE090, BOE100 & BOE101 (p.1/p.23 note, verbatim: "
        "'It is mandatory that for these subjects (BOE100 & BOE101) only Trained Faculty (who had done the "
        "FDP for these courses) will teach the courses.')",
    ],
    "flags": ["hand_transcribed_visible_print"],
}

d["subjects"] = [s for s in d["subjects"] if (s.get("codes") or [""])[0] != "BOE101" or (s.get("name") or s.get("name_print"))]
d["subjects"].append(obj)
d["subjects"].sort(key=lambda o: (o.get("codes") or [""])[0])
json.dump(d, open(P, "w"), indent=1, ensure_ascii=False)
print("BOE101 hand-built;", len(d["subjects"]), "subjects")
