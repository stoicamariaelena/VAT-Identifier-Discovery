# Veridion — Data Assets Intern — VAT Identifier Discovery

## Candidate
Maria-Elena Stoica — Specialist Achiziții & Raportare, Altex (10+ years procurement/reporting/supplier relations, ERP systems: AX, Dynamics 365). Non-traditional background for a data role, but directly lived the "invoice-to-supplier matching" problem operationally. Comfortable with Excel/reporting/data accuracy work; SQL Server (SSMS) being used hands-on for this project.

## The assignment (verbatim brief, condensed for reference — full text also pasted by user in-thread)
A procurement team at a mid-sized manufacturer has 40,000 UK suppliers, matches invoices against them monthly. VAT number is the only reliable cross-reference identifier (appears on both invoice and tax record). They have VAT for ~1/3 of suppliers; the rest match on company name (unreliable — e.g. "J Smith Building Services Ltd" vs "J. Smith Building Svcs Limited").

**Goal:** determine whether a UK company VAT dataset can be built from the open web, and prove it on a sample.

**What makes it hard:**
- HMRC's VAT checker only verifies a given number — it never returns a company's VAT number from its name.
- ~4.2M live UK companies vs ~2.18M VAT registrations (includes sole traders) — so "not found" is ambiguous: not registered vs. discovery failure.
- A wrong number is worse than a missing one (silent corruption vs. visible gap).
- No reference dataset exists to self-check against.

**Deliverable:** one document (README) + supporting code.
- **Part 1 — Research:** sources tried, which work/don't, dead ends with specifics (source, expectation, exact failure reason), not just "scraping is unreliable."
- **Part 2 — Proof of concept:** a representative sample (explain how drawn — NOT cherry-picked companies known to publish VAT), every "found" VAT cross-verified against HMRC's official checker, report measured false-positive rate and how measured.
- **Part 3 — At scale:** what you'd do with real resources (cluster, crawl budget, commercial data, proxies, annotators) — cost/company, what breaks first, production monitoring.
- **Debate topics (thoughts in README, no implementation needed):**
  1. VAT numbers are 9 digits + checksum → brute-forcing against HMRC's checker: feasible? Good idea?
  2. Keeping the dataset current as companies register/deregister.
  3. How would you know the dataset is wrong at scale, with nothing complete to compare against?
  4. Which sources would you NOT be comfortable using in a sold product, and why?
- **Beyond UK (optional):** compare one other country (e.g. Germany) properly rather than a 27-country survey. Discuss what's easier/harder, whether the pipeline survives the move. Identify a country where VAT discovery is nearly impossible and what that implies for market prioritization.

**Guidelines:** ~8-10 hours estimated (flexible). AI tools permitted — reasoning/decisions must be the candidate's own. Must be able to defend abandoned paths and reported numbers in a follow-up conversation. Parts 1 & 3 weighted at least as heavily as Part 2.

**Provided starting points (not exhaustive — finding an unlisted source is a good sign):**
- Companies House bulk data (free monthly snapshot — name, number, address, SIC, incorporation date, accounts category; NO websites, NO VAT).
- HMRC VAT checker (web + bulk API).
- Contexts that legally require publishing a VAT number (to be identified).
- Bulk web corpora (crawling site-by-site may be the wrong shape).
- Adjacent identifiers that might embed/relate to VAT (e.g., EORI numbers, which for UK = GB + VAT + 000 suffix).
- Public records: insolvency notices, public sector spend disclosures, procurement records.
- VIES (EU equivalent of HMRC checker, behaves differently per member state).

## Methodology established so far
- Working from a SQL Server database (`Veridion` table = Companies House bulk data, ~all UK companies) imported by the candidate.
- 40-company sample drawn with: `SELECT TOP 40 * FROM Veridion WHERE CompanyStatus='Active' AND [Accounts.AccountCategory] NOT IN ('DORMANT','NO ACCOUNTS FILED') ORDER BY NEWID()` — genuine random sample, not cherry-picked, representative of the live/active company population (which is why most sampled companies are small/micro — that's realistic, not a sampling flaw).
- Tracker file: `/mnt/user-data/outputs/vat_sample_tracker.csv` — columns: #, CompanyName, CompanyNumber, SIC, WebsiteFound, WebsiteURL, VATFound, VATNumber, HMRCVerified, LikelyExplanation, Confidence, Notes.
  - `LikelyExplanation` categories: Sector exemption / Below VAT threshold / Dormant-shell signal / N/A - VAT confirmed / Uncertain.
  - `HMRCVerified`: whether the VAT number was independently confirmed via the official HMRC checker (critical for the false-positive rate requirement in Part 2).
- Every candidate VAT number found via a secondary source (Endole Open, CompanyData.com, Google AI Overview, vat-lookup.co.uk) is being cross-checked against the official HMRC checker (name + address match) before being accepted — this is the core anti-false-positive discipline the brief demands.
- **SIC code is a weak/last-resort signal for predicting VAT status, not a rule.** It's used only to form an initial soft hypothesis (e.g. "residential care -> plausibly sector-exempt"), always pending independent confirmation. Two confirmed counterexamples in this sample prove SIC-based sector reasoning can be flatly wrong:
  - **Cruden Investments Ltd (SC044986)** — SIC 70100 "Activities of head offices" (holding company). Standard reasoning: pure holding companies with no taxable supplies are typically outside VAT scope, so expected no VAT. Actual: VAT GB268991200 confirmed via HMRC, with the company's own T&Cs page naming the exact company number alongside the VAT number.
  - **Hextable Care Home Limited (09364841)** — SIC 41100 "Development of building projects" (not even a care-sector code), which initially suggested a shell/non-trading entity. Actual: VAT GB211753536 confirmed via HMRC — the company is the genuine holding entity of Cinnamon Care Homes Group.
  - Conclusion for the README: SIC/sector-based reasoning should be treated as a low-weight prior at best, always overridden by direct evidence (company's own site, HMRC check, regulator register) - never used as a standalone classifier for whether a company "should" have VAT.

## Sources evaluated so far
- **HMRC VAT checker (gov.uk/check-uk-vat-number):** official, authoritative. Confirms name+address for a given VAT number, does NOT give a company number. Now requires the requester's own VAT number as a reference (a friction point for bulk/manual use without being VAT-registered yourself).
- **Endole Open (open.endole.co.uk):** free company profiles, sometimes displays VAT number directly tied to the company number — good source when present, but VAT is not always shown, and access gets rate-limited/paywalled ("sign in or come back in 5 minutes") after moderate use — NOT reliable for bulk/scale use without a paid account.
- **CompanyData.com (vat-number-lookup):** free, no signup, searches by name or company number, gives explicit "recorded as VAT-registered" / "not recorded as VAT-registered" status tied to company number. JS-driven search (no working URL query parameter found — can't be automated by simple GET requests, would need an actual API key for the 150-free-calls tier or browser automation). Useful confirmation source when it has data.
- **Google AI Overview / generic web search:** UNRELIABLE — repeatedly produced false or conflated matches (e.g., merged "Lord Kitch Limited" and "Lord Kitch Management Limited" into one incorrect result; surfaced a VAT for a same-named-but-different company for HTC Consultancy). Never trust without independent verification.
- **vat-lookup.co.uk / vat-search.co.uk (third-party aggregators surfaced via search):** unverified reliability, sometimes provide a company number association that doesn't match the actual registered office (dead end / caution flag — see Lord Kitch case).
- **ICO Register of Data Controllers** (`register-of-data-controllers.csv`, ~1.45M rows, uploaded locally, now also queryable via the master SQL DB conceptually) — does NOT give VAT, but useful for: (a) confirming a company is a real, distinct, operating entity at a specific address (cross-check), (b) surfacing trading names not visible in Companies House (e.g., "Graham James Lee Ltd" trades as "Yellow Door Photography" — resolved a postcode discrepancy that turned out to be a one-character typo on the company's own site).
- **SRA register (Solicitors Regulation Authority)** — attempted for a solicitor-SIC company (LA Chambers Ltd), no result found / page errored; not yet a validated source, but conceptually relevant for regulated-profession sub-sectors.
- **LEI (Legal Entity Identifier)** — DEAD END: unrelated to VAT registration entirely (used for financial/MiFID II reporting), most small companies never have one. Confirmed not useful.
- **EORI numbers** — investigated as a promising adjacent identifier (UK EORI = "GB" + VAT number + "000" suffix, so a published EORI would directly yield the VAT). DEAD END so far on this sample: no EORI publicly found for any of the ~4 companies checked (Lord Kitch Limited, M A Motors, Caviar Fresh Fish, ABC Money, Dav Dan, HTC Consultancy) — plausible reason: none of the sampled companies are in goods import/export, so EORI wouldn't apply; worth re-testing on companies actually trading physical goods internationally.
- **WHOIS** (domain registration lookup) — attempted for one ambiguous company-name-to-website match (ABC Money Ltd vs abcmoney.co.uk); registrant was privacy-redacted, so it was a dead end for confirming site ownership, though it did surface a domain-registration-date inconsistency useful for judging "probably not a match."
- **Known mass company-formation / virtual-office addresses** — discovered as a useful negative signal: several sampled companies share registered addresses known to host dozens of unrelated companies (e.g., "First Floor Swan Building, 20 Swan Street, Manchester M4 5JW"; "Office [5-digit number], London") — correlates with shell/small/no-physical-presence companies, supports (but doesn't prove) a "genuinely below VAT threshold" explanation for no-VAT-found cases.
- **Companies House compliance signals** (accounts overdue / confirmation statement overdue) — useful secondary signal for dormant/abandoned company hypothesis when no VAT is found (e.g., ABC Money Ltd — only company in the 40-sample with both overdue).

## Key false-positive case studies (important for Part 1's "dead ends" section)
1. **Lord Kitch Management Limited (13730304)** — target company, SIC 98000 (residents property management). A VAT number (GB309240133) surfaced repeatedly in search, registered at the EXACT same address as the target company. However: HMRC confirms it's registered to "LORD KITCH LIMITED" (different, related company, 11644494, SIC 68100 property trading) — a sister company at the same site, not the target. Google's AI Overview actively conflated the two names into a false single result. This is the clearest illustration in the sample of "a plausible number attached to the wrong company" — address match alone is NOT sufficient proof; company number / name must both be confirmed.
2. **ABC Money Ltd (11390108)** — a plausible website (abcmoney.co.uk) exists with the same name, but founding-year and incorporation-year don't reconcile (2012 site claim vs 2018 incorporation), no registration details link them; WHOIS didn't resolve it either. Treated as coincidental name match, not a confirmed website.
3. **HTC Consultancy Limited (10399697)** — a VAT number surfaced via search but its associated address matched neither the registered office nor the director's correspondence address; no ICO registration either. CompanyData.com, matching directly on company number, explicitly confirmed "not recorded as VAT-registered" — a clean negative result reached only by insisting on company-number-level matching rather than name/fuzzy matching.

## Sample progress (as of this writing — see tracker CSV for full detail)
**40 of 40 companies processed — sample complete.** Notable confirmed-VAT cases (all HMRC cross-verified): Rachel Anderson Consulting Ltd (GB103354850), PAV Fixers Ltd (GB137451515), Graham James Lee Ltd (GB198427950, trading as Yellow Door Photography / Graham Lee Photography), R W Evans & Son Ltd (GB869464075, Ltd/Limited name-abbreviation nuance noted and accepted), Caviar Fresh Fish Ltd (GB407333029), Hextable Care Home Ltd (GB211753536, part of Cinnamon Care Homes Group), Cruden Investments Ltd (GB268991200), Hapsoft Consulting Ltd (GB208341433, gold-standard case — own site lists company number + VAT together), Cityfleet Networks Ltd (GB775069400, confirmed via Endole + HMRC; not published on company's own T&Cs page). Several "not found" cases categorized with a likely explanation and confidence level (Sector exemption / Below VAT threshold / Dormant-shell signal / Uncertain) rather than left as flat gaps — directly addressing the brief's "not found ≠ not registered" ambiguity concern. Multiple confirmed false-lead/naming-trap cases logged (Lord Kitch, HTC Consultancy, M A Motors vs M&A Cars, Dogstuff Ltd vs Dogstuff.co.uk Ltd, L.J.V. Consultants vs LJ Consultants/L-J Consulting, O'Neill Properties Ltd vs O'Neill Property).

**Final Part 2 statistics (computed from the corrected tracker CSV — a 3-row CSV-quoting bug, unquoted commas inside the WebsiteURL field for #8/#19/#40, was found and fixed before computing these; Graham James Lee Ltd's HMRC check result had also already been provided earlier and is now correctly recorded as fully confirmed, not pending):**
- Sample size: 40 (random, `ORDER BY NEWID()`, active/non-dormant companies only — see Methodology above).
- **Coverage rate = 9/40 = 22.5%** — share of the sample for which a usable VAT number was found from open-web sources.
- All 9 independently confirmed via the official HMRC checker — returned registered name + address matched the target company's Companies House registered office exactly in every case.
- **False-positive rate = 0/9 = 0%** among VATs put forward as a match — every VAT number tested against the HMRC checker matched the target company's name/address exactly; none belonged to a different (e.g., similarly-named) company. Measured by: for each VAT candidate, entering it in HMRC's official checker and comparing the returned registered name + address against the company's Companies House registered office; a mismatch or "not found" would have been logged as a false positive (none occurred in this sample) — the *closest* thing to a false positive in the whole exercise was the Lord Kitch case, a candidate rejected before being counted (a VAT number that belonged to a sister company, not the target) — worth narrating in the README as evidence the discipline works, not as a false positive since it never entered the "confirmed" bucket.
- Website found (Yes/Likely): 16/40 (40%); Uncertain: 3/40; No (incl. 1 "closed"): 21/40.
- Of the 31 no-VAT-found cases: 13 "Below VAT threshold", 5 "Sector exemption", 3 "Dormant/shell signal", 10 "Uncertain" (no confident explanation reached).

## Companies House: bulk data vs. live site access (important distinction for Part 1/3)
Two completely different access paths to the same institution, with very different reliability:
- **Bulk data product** (the `Veridion` table, downloaded once as a monthly snapshot file) - fully reliable, no rate limits, this is how the entire 40-company sample's base data (name, number, address, SIC, etc.) was obtained. Static, not live.
- **Live website** (find-and-update.company-information.service.gov.uk, the human-facing lookup interface) - queried ad-hoc, one page at a time, to fill gaps the bulk export doesn't have (full filing history detail, live status changes, etc.). This channel has anti-bot/rate-limiting protections and returned intermittent 403 errors throughout the later half of this sample (Anglo-Gulf Agencies, O'Neill Properties, L.J.V. Consultants, among others) - not a data-quality problem, an access-channel problem.
Implication for Part 3 (at scale): the official bulk snapshot is the reliable backbone for base company data; supplementing it with live-site scraping for anything beyond the snapshot's fields is exactly the kind of ad-hoc access that breaks first at volume. A production pipeline would want either an official bulk/API data product for any supplementary Companies House data (if one exists) or accept that live-page lookups need to be rate-limited/retried/queued, not fetched synchronously per-company.

## Ethics/sourcing note for debate topic 4 ("which sources would you NOT be comfortable using")
Several sampled companies are essentially personal-name businesses (e.g. Paul Walker ECI Limited, #35) - the director's own name IS the company name. Researching these by open web search means searching a real individual's name directly, which:
- surfaces unrelated same-named people (actors, footballers, other unrelated Paul Walkers) - noise, but also a real risk of misattributing information from an unrelated person to the wrong small business owner;
- crosses from "looking up a company" into "profiling a private individual" - even though the underlying fact (director name) is legitimately public via Companies House, broad open-web name search goes further than that registry lookup and pulls in whatever else the internet associates with that name.
Companies House/HMRC/regulator-register lookups (querying by company number or exact registered name) stay clearly in "business record" territory. A generic open-web search of a sole trader's personal name is a source to flag as uncomfortable/inappropriate for a commercial product - it's disproportionate to the actual need (a VAT number) and blurs into personal-data profiling. Practical implication for Part 3: an at-scale pipeline should avoid free-text web search of director names entirely and rely only on structured, business-scoped sources (company number/registered name queries against official/regulatory registers).

## Immediate next steps
- Sample research is complete (40/40) and Part 2 statistics are computed (see above). Remaining work is all write-up:
- Draft README.md addressing Parts 1–3 and the four debate topics, using this file + the tracker CSV as source material.
- Optional: attempt the "Beyond the UK" comparison (Germany suggested in the brief) if time allows — note: ExploreZanzi.com Ltd (#28) already surfaced a related cross-border nuance (UK company, Tanzania-delivered service, TOMS scheme) worth folding into this section.
