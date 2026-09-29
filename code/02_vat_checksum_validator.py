"""
UK VAT number format + checksum validator.

Standalone, no dependencies. Implements the two check-digit algorithms
HMRC has used for standard 9-digit UK VAT numbers:

  - "Mod 97"   — the original algorithm.
  - "Mod 9755" — a second valid algorithm introduced once the numeric
                  range for the original scheme started running out
                  (roughly 2009-2010 onwards); a number can validly pass
                  under either scheme, so both are checked.

WHAT THIS SCRIPT IS FOR (and, importantly, what it is NOT for):

  This is a *plausibility filter*, not a verification tool. A number
  that passes this check is well-formed and internally consistent —
  it is NOT confirmed to belong to any real company, let alone the
  target company. Every VAT number in the Part 2 sample was still
  independently confirmed against HMRC's official "Check a UK VAT
  number" service (name + address match), which is the only source
  in this project that actually proves attribution. See the README's
  answer to debate topic 1 for why brute-forcing this checksum space
  is not, on its own, a viable discovery strategy: this validator
  demonstrates exactly why — the "valid-checksum" space is far larger
  than the register of numbers actually issued to a company, so a
  checksum pass tells you a number *could* be real, never that it is,
  or whose it is.

Known limitation: this does not handle the special GD (government
department, GB GD001-GB GD499) or HA (health authority, GB HA500-
GB HA999) number formats, which don't follow the digit-checksum
scheme at all. None of the 40 sampled companies used these, so it
wasn't worth building out for this project, but a production
implementation should account for them.
"""

import re
import sys

VAT_RE = re.compile(r"^(GB)?(\d{9})(\d{3})?$")


def normalise(raw: str) -> str | None:
    """Strip whitespace/prefix, return the bare 9-digit core, or None if malformed."""
    cleaned = raw.strip().upper().replace(" ", "")
    match = VAT_RE.match(cleaned)
    if not match:
        return None
    return match.group(2)


def checksum_valid(nine_digits: str) -> bool:
    """True if the 9 digits pass either the Mod 97 or Mod 9755 check-digit scheme."""
    digits = [int(c) for c in nine_digits]
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(d * w for d, w in zip(digits[:7], weights))
    check_digits = digits[7] * 10 + digits[8]

    def passes(t: int) -> bool:
        remainder = t % 97
        expected = (97 - remainder) % 97
        return expected == check_digits

    return passes(total) or passes(total + 55)


def validate(raw: str) -> dict:
    """
    Returns a dict describing the validation result. Never raises on bad
    input — always returns a structured verdict, since this is meant to
    run unattended over a batch of candidate numbers.
    """
    core = normalise(raw)
    if core is None:
        return {"input": raw, "well_formed": False, "checksum_valid": False,
                "verdict": "malformed - not 9 (or 9+3) digits, optionally GB-prefixed"}

    ok = checksum_valid(core)
    return {
        "input": raw,
        "well_formed": True,
        "checksum_valid": ok,
        "verdict": "plausible - still requires HMRC verification for attribution" if ok
                   else "checksum fails - not a valid UK VAT number as formatted",
    }


if __name__ == "__main__":
    # Sanity-check against the 9 VAT numbers this project actually confirmed
    # via HMRC (see vat_sample_tracker.csv) - every one of these should come
    # back checksum-valid, since they're real, currently-issued numbers.
    confirmed_from_sample = [
        "GB103354850",  # Rachel Anderson Consulting Ltd
        "GB137451515",  # PAV Fixers Ltd
        "GB198427950",  # Graham James Lee Ltd
        "GB869464075",  # R W Evans & Son Ltd
        "GB407333029",  # Caviar Fresh Fish Ltd
        "GB211753536",  # Hextable Care Home Ltd
        "GB268991200",  # Cruden Investments Ltd
        "GB208341433",  # Hapsoft Consulting Ltd
        "GB775069400",  # Cityfleet Networks Ltd
    ]

    numbers = sys.argv[1:] if len(sys.argv) > 1 else confirmed_from_sample
    all_ok = True
    for n in numbers:
        result = validate(n)
        status = "OK" if result["checksum_valid"] else "FAIL"
        if not result["checksum_valid"]:
            all_ok = False
        print(f"[{status}] {n:20s} -> {result['verdict']}")

    if numbers is confirmed_from_sample:
        print()
        print("All 9 HMRC-confirmed sample VATs checksum-valid."
              if all_ok else
              "WARNING: at least one HMRC-confirmed VAT failed checksum - "
              "re-check the algorithm before trusting this validator.")
