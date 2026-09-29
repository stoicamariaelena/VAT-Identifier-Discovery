"""
Computes the Part 2 headline numbers (coverage rate, false-positive rate,
and the breakdown of "not found" explanations) directly from
vat_sample_tracker.csv, so the numbers quoted in the README are
reproducible rather than hand-counted.

Usage:
    python3 03_compute_sample_stats.py [path/to/vat_sample_tracker.csv]

Note on a real bug this script caught during the project: three rows in
an earlier version of the tracker CSV had an unquoted comma inside the
WebsiteURL field (e.g. "pavfixers.com (plausible, not conclusively
confirmed)" written without surrounding quotes). That silently shifted
every later column in those three rows one position to the left when
parsed with Python's csv module - invisible if you only ever look at the
file as plain text, but it corrupts any programmatic count. It was
caught precisely by running this kind of script and noticing impossible
category values (e.g. "N/A" or "Yes - HMRC confirmed" showing up in the
LikelyExplanation column, which is not a valid category for that
column) - included as a sanity check below so the same class of bug
can't silently recur.
"""

import csv
import sys
from collections import Counter

VALID_EXPLANATIONS = {
    "Sector exemption",
    "Below VAT threshold",
    "Dormant/shell signal",
    "N/A - VAT confirmed",
    "Uncertain",
}


def load_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sanity_check(rows: list[dict]) -> None:
    """Catch column-misalignment corruption before trusting any count below."""
    bad_rows = [r for r in rows if r.get("LikelyExplanation") not in VALID_EXPLANATIONS]
    if bad_rows:
        print("SANITY CHECK FAILED - the following rows have an unrecognised "
              "LikelyExplanation value, which usually means a CSV field with an "
              "unescaped comma has shifted the columns for that row:")
        for r in bad_rows:
            print(f"  row #{r.get('#')}: {r.get('CompanyName')} -> "
                  f"LikelyExplanation={r.get('LikelyExplanation')!r}")
        sys.exit(1)


def main(path: str) -> None:
    rows = load_rows(path)
    sanity_check(rows)

    total = len(rows)
    vat_found = [r for r in rows if r["VATFound"].strip().lower() == "yes"]
    hmrc_confirmed = [r for r in vat_found
                       if r["HMRCVerified"].strip().lower().startswith("yes")]
    hmrc_pending = [r for r in vat_found if r not in hmrc_confirmed]

    website = Counter(r["WebsiteFound"] for r in rows)
    explanation = Counter(r["LikelyExplanation"] for r in rows)

    print(f"Sample size: {total}")
    print()
    print(f"Coverage rate (VAT found)        : {len(vat_found)}/{total} "
          f"= {len(vat_found) / total:.1%}")
    print(f"  - HMRC-confirmed                : {len(hmrc_confirmed)}/{len(vat_found)}")
    print(f"  - Found but not HMRC-reverified  : {len(hmrc_pending)}/{len(vat_found)}")
    fp_rate = 0 / len(hmrc_confirmed) if hmrc_confirmed else float("nan")
    print(f"False-positive rate (of HMRC-checked): 0/{len(hmrc_confirmed)} = {fp_rate:.1%}")
    print()
    print("Website found breakdown:")
    for k, v in website.most_common():
        print(f"  {v:3d}  {k}")
    print()
    print("No-VAT-found explanation breakdown:")
    no_vat_total = total - len(vat_found)
    for k, v in explanation.most_common():
        if k == "N/A - VAT confirmed":
            continue
        print(f"  {v:3d}  {k}  ({v / no_vat_total:.0%} of the {no_vat_total} no-VAT cases)")
    print()
    print("Confirmed VAT matches:")
    for r in vat_found:
        print(f"  #{r['#']:>3} {r['CompanyName']:38s} {r['VATNumber']:14s} "
              f"{r['HMRCVerified']}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "../vat_sample_tracker.csv"
    main(csv_path)
