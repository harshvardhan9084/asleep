#!/usr/bin/env python3
"""patch_b20_verify_flags.py — B20 verifier-finding patches (CRON-20261101-B20).

Every patch records its printed evidence (RULES §4/§6); the flag strings are
the classes verify_draft.py already downgrades (B2/B8/v11/v12/v13/v14 remedies).

1. docs 01/02/03/05/06 no-units subjects: project/mini-project/seminar/
   industrial-training/startup subjects print NO unit theory by design.
   - cos printed  -> `co_only_no_units_printed` (v11 class, B08 evidence)
   - nothing printed beyond the scheme row -> `detailed_syllabus_not_printed`
     (B2 class, B02/B18/B19 evidence)
2. doc 08 BCS353 Web Designing Workshop: raster pp.12-15 (empty text layer).
   Transcribed by the run agent from page-image reads (pp.12-15) per RULES §6
   (visible print authoritative): "Syllabus:" bullet-block design — 4 topic
   blocks (HTML / CSS / BOOTSTRAP / JavaScript, no Unit-I..V labels, no CO
   table), 2 textbooks, 2 reference books, experiments 1-10. Blocks recorded
   as units 1-4 in printed order (same mapping as draft 09's OCR pass of the
   identical 2025-26 print). Flag `unit_ocr_recovered_no_text_layer` (v12/v13
   class) with page-citing quirks.
3. doc 08 BCC301/BCC302: prior flag wrongly attributed detailed-syllabus
   pages — page-image reads prove pp.12-15 carry ONLY BCS353; BCC301/BCC302
   print ONLY in the scheme table row SN 10 (p.2). Detailed syllabus of these
   common subjects is printed in the 2nd-year common doc (ingested B01,
   sha 13bd875d098f99df). needs_review replaced with the recorded
   scheme_row_only class + corrected attribution quirk.
4. doc 09 BCS353: OCR-recovered from scanned pp.11-14 (300-1200 dpi with
   word-crop adjudication, quirks already on the subject) — flag
   `unit_ocr_recovered_no_text_layer` added so v12/v13 downgrades apply.
"""
import json, os, sys

D = "/home/z/my-project/work/pipeline_v2/drafts"


def load(stem):
    return json.load(open(os.path.join(D, stem + ".draft.json")))


def save(stem, d):
    with open(os.path.join(D, stem + ".draft.json"), "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)


def find(d, code):
    for s in d["subjects"]:
        if code in (s.get("codes") or []):
            return s
    raise SystemExit(f"subject with code {code} not found")


def add_flag(s, flag, quirk):
    fl = s.setdefault("flags", [])
    if flag not in fl:
        fl.append(flag)
    qs = s.setdefault("quirks", [])
    if quirk not in qs:
        qs.append(quirk)


def main():
    n = 0

    # ---- doc 01: 4 scheme-only subjects (no CO table anywhere in the doc) ----
    stem = "01_btech_cse_y4_syllabus-cbcs_2019-20"
    d = load(stem)
    for code, nm in (("RCS753", "Industrial Training"), ("RCS754", "Project"),
                     ("RCS851", "Seminar"), ("RCS852", "Project")):
        s = find(d, code)
        add_flag(s, "detailed_syllabus_not_printed",
                 "patch-b20: scheme-row-only print (verifier B02/B18/B19 no-units class): "
                 f"{nm} ({code}) prints in the Sem-VII/VIII scheme table and totals rows "
                 "only; no detailed page, no CO table printed anywhere in the document.")
        n += 1
    save(stem, d)

    # ---- doc 02: 3 CO-only subjects (BCS754H Startup already flagged) ----
    stem = "02_btech_cse_y4_syllabus-hindi_2025-26"
    d = load(stem)
    for code, nm in (("BCS752H", "Mini Project or Internship Assessment"),
                     ("BCS753H", "Project-I"), ("BCS851H", "Project-II")):
        s = find(d, code)
        assert s.get("cos"), f"{code} expected printed CO block"
        add_flag(s, "co_only_no_units_printed",
                 "patch-b20: CO-block-only print (verifier v11 B08 class): "
                 f"{nm} ({code}) prints a real course-outcome table but no unit theory "
                 "anywhere in the document — printed design of project/assessment courses.")
        n += 1
    save(stem, d)

    # ---- doc 03: 2 CO-only subjects ----
    stem = "03_btech_cse_y4_syllabus_2021-22"
    d = load(stem)
    for code, nm in (("KCS354", "Mini Project or Internship Assessment"),
                     ("KCS753", "Project")):
        s = find(d, code)
        assert s.get("cos"), f"{code} expected printed CO block"
        add_flag(s, "co_only_no_units_printed",
                 "patch-b20: CO-block-only print (verifier v11 B08 class): "
                 f"{nm} ({code}) prints a course-outcome table; no unit theory printed "
                 "in the document.")
        n += 1
    save(stem, d)

    # ---- doc 05: 3 CO-only + 1 scheme-only ----
    stem = "05_btech_csit-ce-it_y4_syllabus_2025-26"
    d = load(stem)
    for code, nm in (("BIT752", "Mini Project or Internship Assessment"),
                     ("BIT753", "Project-I"), ("BIT851", "Project-II")):
        s = find(d, code)
        assert s.get("cos"), f"{code} expected printed CO block"
        add_flag(s, "co_only_no_units_printed",
                 "patch-b20: CO-block-only print (verifier v11 B08 class): "
                 f"{nm} ({code}) prints a course-outcome table; no unit theory printed "
                 "in the document.")
        n += 1
    s = find(d, "BIT754")
    add_flag(s, "detailed_syllabus_not_printed",
             "patch-b20: scheme-row-only print (verifier B02/B18/B19 no-units class): "
             "Startup and Entrepreneurial Activity Assessment (BIT754) prints in the "
             "Sem-VII scheme table only; no detail page, no CO table in the document.")
    n += 1
    save(stem, d)

    # ---- doc 06: KCS354 scheme-only ----
    stem = "06_btech_csit-cse_y2_model-curriculum_2019-20"
    d = load(stem)
    s = find(d, "KCS354")
    add_flag(s, "detailed_syllabus_not_printed",
             "patch-b20: scheme-row-only print (verifier B02/B18/B19 no-units class): "
             "Mini Project or Internship Assessment (KCS354) prints in the Sem-III/IV "
             "scheme tables only; no detailed page in the document.")
    n += 1
    save(stem, d)

    # ---- doc 08: BCS353 full page-image transcription + BCC301/302 flag fix ----
    stem = "08_btech_cyber-security_y2_syllabus_2026-27"
    d = load(stem)
    s = find(d, "BCS353")
    s["units"] = {
        "1": ("HTML: Elements, attributes, heading, paragraph, styles, comments, links, "
              "images, favicon, tables, list, class, id, HTML forms, HTML media, "
              "navigation bar."),
        "2": ("CSS: Types of CSS, colors, background, margins, padding, height, width, "
              "text, font, icon, links, list, tables, display, z-index, float, overflow, "
              "CSS media queries, inline block, navigation bar, image gallery, forms, "
              "round corners"),
        "3": ("BOOTSTRAP : Fundamentals of implementing responsive web design ,Use "
              "Balsamiq to mockup and wireframe websites, The fundamentals of UI design "
              "for websites ,How to install the Bootstrap framework ,Understanding the "
              "Bootstrap grid layout system, How to use bootstrap containers to layout "
              "your website easily, Use other Bootstrap components such as buttons ,"
              "Adding symbols using Font Awesome, Bootstrap carousels. Add Bootstrap "
              "cards to your website. Using Bootstrap navigation bars,"),
        "4": ("JavaScript: script, function, output, statement, variables, operators, "
              "datatypes, objects, events, string methods, Arrays, if else, switch, "
              "loop for, loop in, loop for, debugging, validation of forms , Functions "
              "and invocation patterns Discussion of ECMAScripts Intermediate JavaScript "
              ", JS Expressions, Operators, Statements and Declarations , Object-Oriented "
              "Programming JS Objects and Prototypes, `This`, Scope and Closures Objects "
              "and Prototypes Refactoring and Debugging"),
    }
    s["textbooks"] = [
        {"no": 1, "book": ("Meloni, J. C., Kyrnin, J. (2018). HTML, CSS, and JavaScript "
                           "All in One: Covering HTML5, CSS3, and ES6, Sams Teach "
                           "Yourself. United Kingdom: Pearson Education.")},
        {"no": 2, "book": ("McGrath, M. (2020). HTML, CSS & JavaScript in easy steps. "
                           "United Kingdom: In Easy Steps Limited.")},
    ]
    s["reference_books"] = [
        {"no": 1, "book": ("Duckett, J. (2014). Web Design with HTML, CSS, JavaScript "
                           "and JQuery Set. United Kingdom: Wiley.")},
        {"no": 2, "book": ("Fajfar, I. (2015). Start Programming Using HTML, CSS, and "
                           "JavaScript. United Kingdom: CRC Press.")},
    ]
    s["experiments"] = [
        {"no": 1, "exp": ("Designthefollowingstaticwebpagesrequiredforanonlinebookstore"
                          "website. HOMEPAGE: The static home page must contain three "
                          "frames. Top frame: Logo and the college name and links to Home "
                          "page, Login page, Registration page and Cart page (the "
                          "description of these pages will be given below). For example: "
                          "When you click the link \u201cCSE\u201d the catalogue for CSE "
                          "Books should be displayed in the Right frame. Right frame: The "
                          "pages to the links in the left frame must be loaded here. "
                          "Initially this page contains description of the web site.")},
        {"no": 2, "exp": ("LOGINPAGE: This page looks like below: printed sample login "
                          "page (Logo/WebSite Name banner, Home/Login/Registration/"
                          "Catalogue/Cart bar, branch list CSE EEE ECE CIVIL, Login Page "
                          "with User Name:, Passwords: fields, Submit and Reset buttons).")},
        {"no": 3, "exp": ("CATOLOGUE PAGE: The catalogue page should contain the details "
                          "of all the books available in the website in a table. The "
                          "details should contain the following: 1. Snap shot of Cover "
                          "Page. 2. Author Name. 3. Publisher. 4. Price. 5. Add to cart "
                          "button.")},
        {"no": 4, "exp": ("CARTPAGE: The cart page contains the details about the books "
                          "which are added to the cart. The cart page should look like "
                          "this: printed sample table (Book name/Price/Quantity/Amount — "
                          "Java 2 $35.5 2 $70; XML bible $40.5 1 $40.5; Total amount "
                          "-$130.5).")},
        {"no": 5, "exp": ("REGISTRATION PAGE : Create a\u201d registration form\u201d with "
                          "the following fields 1)Name (Text field) 2)Password (password "
                          "field) 3) E-mailid(text field) 4) Phone Number(text field) "
                          "5) Sex(radio button) 6) Date of birth(3 select boxes) "
                          "7) Languages known(checkboxes\u2013English, Telugu, Hindi, "
                          "Tamil) 8) Address(text area)")},
        {"no": 6, "exp": ("Js VALIDATION: Write JavaScript to validate the following "
                          "fields of the above registration page. 1. Name (Name should "
                          "contains alphabets and the length should not be less than 6 "
                          "characters). 2. Password (Password should not be less than 6 "
                          "characters length).")},
        {"no": 7, "exp": ("Js VALIDATION: 3. E-mailid (should not contain any invalid "
                          "and must follow the standard pattern(name@domain.com) 4. Phone "
                          "Number(Phone number should contain 10 digits only).")},
        {"no": 8, "exp": ("CSS: Design a web page using CSS(Cascading Style Sheets) which "
                          "includes the following: 1) Use different font, styles: In the "
                          "style definition you define how each selector should work(font, "
                          "color etc.). Then, in the body of your pages, you refer to "
                          "these selectors to activate the styles. 2) Set a background "
                          "image for both the page and single elements on the page.")},
        {"no": 9, "exp": ("CSS: 1) Control the repetition of the image with the "
                          "background-repeat property. 2) Define styles for links as "
                          "A:link A:visited A:active A:hover")},
        {"no": 10, "exp": ("Consider a small topic of your choice on which you can develop "
                           "static Webpages and try to implement all topics of html, CSS "
                           "and Js within the topic. Choose any one topic. 1. Your Own "
                           "Portfolio 2. To-Do List 3. Survey Form 4. A Tribute Page "
                           "5. A Questionnaire")},
    ]
    fl = s.get("flags") or []
    s["flags"] = [f for f in fl if not str(f).startswith("needs_review")]
    s["flags"].append("unit_ocr_recovered_no_text_layer")
    s.setdefault("quirks", []).extend([
        ("patch-b20 (pp.12-15 page-image transcription, RULES \u00a76 visible print): "
         "BCS353's detailed page prints a \u201cSyllabus:\u201d bullet-block design — 4 "
         "topic blocks (HTML / CSS / BOOTSTRAP / JavaScript) with NO Unit-I..V labels, "
         "NO CO table, NO printed L-T-P/credit row; blocks recorded as units 1-4 in "
         "printed order (same mapping as draft 09's OCR pass of the identical 2025-26 "
         "BCS353 print)."),
        ("patch-b20 (pp.12-15): Textbook/Reference/List-of-Experiments sections print as "
         "raster tables; experiment rows 1-10 transcribed from page images including the "
         "printed sample-layout descriptions (merged-space row label "
         "'Designthefollowingstaticwebpagesrequiredforanonlinebookstorewebsite.', "
         "'CATOLOGUE PAGE' misspelling kept verbatim, experiment 1 spans pp.12-13)."),
    ])
    s["locator"] = (s.get("locator") or "") + "; detailed syllabus transcribed from raster pp.12-15 page images (patch-b20)"
    n += 1

    s = find(d, "BCC301")
    fl = s.get("flags") or []
    s["flags"] = [f for f in fl if not str(f).startswith("needs_review")]
    s["flags"].append("scheme_row_only_in_this_doc_detailed_syllabus_printed_in_2ndyr_common_doc")
    qs = s.setdefault("quirks", [])
    qs.append("patch-b20 page-image correction: pp.12-15 carry ONLY BCS353 (Web Designing "
              "Workshop) content — the prior needs_review attribution of 'raster pp.13-15' "
              "to BCC301/BCC302 was wrong and is withdrawn. BCC301/BCC302 print ONLY in "
              "the Semester-III scheme table row SN 10 (p.2); the detailed syllabi of "
              "these 2nd-year common subjects are printed in the common-subjects doc "
              "(ingested B01, sha 13bd875d098f99df, BCC301/401+H Cyber Security and "
              "BCC302/402+H Python) — not re-extractable from this document.")
    n += 1
    save(stem, d)

    # ---- doc 09: BCS353 OCR-recovery flag ----
    stem = "09_btech_ds_y2_syllabus_2025-26"
    d = load(stem)
    s = find(d, "BCS353")
    add_flag(s, "unit_ocr_recovered_no_text_layer",
             "patch-b20: unit_ocr_recovered_no_text_layer applied — pages 11-14 are "
             "full-page scans (empty text layer); content recovered by OCR at 300-1200 "
             "dpi with word-crop adjudication (quirks below).")
    n += 1
    save(stem, d)

    print(f"PATCHED|{n} subjects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
