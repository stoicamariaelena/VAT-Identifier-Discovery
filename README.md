# VAT Identifier Discovery — Can a UK VAT Dataset Be Built From the Open Web?

**Candidate:** Maria-Elena Stoica

**Assignment:** Data Assets Intern, Veridion

**Time spent:** ~10 hours

**How this was worked:** I used AI (Claude) throughout, as allowed by the brief — but I checked everything myself, I did not just accept its answers. For all 40 companies, I did my own searches on Endole, company websites, and Companies House, in parallel with the AI, and compared results. Several corrections in the tracker (for example, the VAT numbers for Caviar Fresh Fish Ltd and Cruden Investments Ltd) came from things I found myself that the AI had missed or got wrong. Every HMRC VAT check in Part 2 was done by hand, by me, on the real HMRC form (it needs a person to fill it in, it can't be automated) — I ran each check myself and wrote down the real result. The SQL query and database were also built and debugged together. The AI helped write the text and the code, and helped me search faster. But the checking, the decisions, and a large part of the research were mine.

## Summary

Short answer: **it works partly, and only if the limits are stated clearly.** I took a real random sample of 40 active UK companies. Using open-web sources, I found a VAT number I could verify for 9 of them (22.5%). All 9 were confirmed exactly by HMRC's official checker — a 0% false-positive rate. But this 0% shows the checking process works well, it does not mean coverage is high. For the other 77.5%, some are companies that likely never will have a findable VAT number (they're below the threshold, or in an exempt sector), and some are companies where I just couldn't find enough evidence to say anything for sure. Both groups are real and about the same size. No amount of automation fixes the second group — that needs more time, people, and money (see Part 3).

The main point I want the reader to take from this: **"VAT not found" is not one single result. It's at least four different situations** (below the registration threshold, sector exemption, genuinely can't be found on the open web, or my search simply failed). A real production system needs to keep track of which one applies, not just leave a blank.

---

## Part 1 — Research

### Before the random sample: testing the approach on companies I already knew

Before building the random 40-company sample used in Part 2, I first tested the general approach on a smaller, hand-picked set of companies, on purpose — this was about learning which sources work at all and how they relate to each other, not about measuring coverage (coverage is only ever measured on the random sample, never on these).

I started by loading the Companies House bulk file into MySQL and filtering it down to SIC codes 35130 and 63110 (active companies only, excluding dormant ones and ones with no accounts filed), which gave 569 companies. This was just a way to get a manageable, realistic list of real companies to test sources against, not a sample for measuring anything.

Two individual companies from this testing phase are worth describing, because they surfaced things the random sample alone didn't:

- **TTC Group Services Ltd (ZA826434).** The ICO register gave an address that matched HMRC's records, while the Companies House address didn't — a sign the ICO data can sometimes be more current. Searching for its VAT number also surfaced a naming trap: results came back for **TTC GROUP (UK) LIMITED** (06214074), a different company. vat-lookup.co.uk itself was down (connection timeout), but Google still showed old, cached snippets from it — stale data from a source I could no longer check. I eventually found the real VAT number (GB279365945) via **Creditsafe's** public business-index page, confirmed exactly with HMRC.
- **Vistra Ltd (865285).** Searching Google for the company number, name, and "VAT" together found the company's own terms-and-conditions PDF: "Registered in England and Wales No. 865285. VAT No GB 927 5031 30" — confirmed exactly with HMRC. Like a few other cases in the main 40-company sample (see Part 2), the company number and VAT number were found sitting side by side in the company's own document — the strongest type of evidence available, since a single source confirms identity and VAT together. It also surfaced a normalisation issue I saw on other companies' sites too, not just this one: official documents often drop the leading zeros from a company number (865285, vs. Companies House's 00865285). I confirmed this is a real practical risk myself — I put the raw CSVs into Excel Online, and it automatically stripped the leading zeros from every company number, unless I manually formatted that column as text first.

What this early testing phase taught me, in general: **a name match is the main signal that matters, and an address mismatch on its own is not a warning sign** (it often just means a different, correct part of the same business, like a registered office versus a trading address). **Companies that are part of a group are the single biggest source of false-positive risk** — a VAT number can be completely real and completely wrong for your target, because it belongs to a related company in the same group (see the Lord Kitch case below, and the TTC Group case above). One more thing worth pointing out about Companies House, which came up repeatedly: the registered address on file could be the company's accountant's address, or a virtual office — not necessarily the real place the business operates. I can't say for sure which it is in every case, but it's common enough that a mismatch between the registered address and a company's real trading address should be treated as normal and expected, not a red flag by itself.

### Sources tried

| Source | What it gives you | Verdict |
|---|---|---|
| **Companies House — bulk "Free Company Data Product"** | Name, number, registered address, SIC code, incorporation date, accounts category, for almost all live UK companies | **The reliable base.** No rate limits, but no VAT or website fields. This is the full table (`Veridion` in my SQL Server database) that the 40-company sample was drawn from. One thing worth pointing out: the registered address could be the company's accountant's address, or a virtual office, not necessarily where the business actually operates — so it shouldn't be treated as a "real" trading address on its own. |
| **Companies House — live website** (find-and-update.company-information.service.gov.uk) | Full filing history and current status — not VAT or a website, but useful when the bulk file's monthly snapshot might be out of date (a changed address, a new status flag) | **Same organisation, very different reliability.** It blocked the AI's automated checks repeatedly (403 errors) in the second half of the project — on Anglo-Gulf Agencies, O'Neill Properties, L.J.V. Consultants, and others. I didn't personally run into this problem on Companies House itself when checking by hand. This is a problem with how you access it, not a problem with the data itself — see Part 3. |
| **HMRC "Check a UK VAT number"** (gov.uk/check-uk-vat-number) | Confirms the *name and address* for a VAT number you already have | The only source in this whole project that can truly prove a match. It only works one way — you cannot ask it "what is this company's VAT number." It now also asks for the *requester's own VAT number* before it will run a check, which is a real obstacle if you're not VAT-registered yourself and want to do this often. All 9 confirmed VAT numbers below were checked here, by hand. One practical note: the checker accepts a VAT number without the "GB" prefix, and it doesn't matter whether spaces are included between digits — worth knowing if you're normalising numbers from different sources before checking them. |
| **Endole Open** (open.endole.co.uk) | Free company profile pages; sometimes shows a VAT number next to the company number | The single best free source for *finding* a possible VAT number — but it doesn't always show one, and it blocks you after moderate use in one session, with a "we're busier than usual" message, a 15-minute timer, and an option to log in instead. I ran into this myself, checking by hand, not just in automated checks. Not usable at large scale without changes. |
| **CompanyData.com** (VAT number lookup) | Tells you clearly "recorded as VAT-registered" or "not recorded as VAT-registered," by company number | Useful for *ruling companies out* (this is how I cleanly ruled out HTC Consultancy and LA Chambers). But the free search uses JavaScript and has no simple web address to search by — you'd need the paid version or a browser-automation tool to run it automatically. |
| **vat-lookup.co.uk / vat-search.co.uk** (other websites that collect VAT data) | Found through general search | I don't know where their data comes from, and one of them was directly involved in a false lead (see the Lord Kitch case below). When I tried opening vat-lookup.co.uk directly, the site itself was down (a connection timeout) — but Google was still showing old, cached snippets of its data in search results, meaning you can be shown stale data from a source that's no longer even live or checkable. Never trusted without checking against HMRC first. |
| **Creditsafe** (public business-index pages, a commercial credit-reference company) | Company profile pages, sometimes including a VAT number | Worked the one time I properly tested it — found a VAT number that HMRC then confirmed exactly. Only tested on 1 company so far, so I can't say how often it has the VAT number, but worth including in a bigger source list. It's a commercial company, so before using it in a real product, someone would need to check its terms of use and whether that use is actually allowed. |
| **Google / AI Overview / normal web search** | — | **Actively unreliable, not just messy.** It mixed up two different, similarly-named companies (Lord Kitch Ltd and Lord Kitch Management Ltd) into one wrong answer. It also gave a VAT number for the wrong HTC Consultancy company. I only used it to find leads, never to confirm anything. |
| **ICO Register of Data Controllers** (about 1.45 million rows) | Doesn't give VAT numbers, but confirms a company is real and operating, and sometimes shows a trading name that Companies House doesn't | This is how I solved the Graham James Lee Ltd / "Yellow Door Photography" trading-name case, and even caught a typo in a postcode on the company's own website. |
| **Sector regulator registers** (CQC for care homes, GPhC for pharmacies, SRA for solicitors, FCA for financial advisers) | Independent, official confirmation that a company is real, currently operating, and regulated, at a specific address | Worked well every time I used it (Hextable Care Home through its group connection, Kiam Pharmacy, KB Wealth Planning's FCA number). Checking LA Chambers Ltd against the SRA register came back empty — I treated that as a supporting sign it might not be trading, not as proof it doesn't exist. |
| **EORI numbers** (a UK EORI number = "GB" + the VAT number + "000") | Would give me the VAT number directly, if published | **Dead end in this sample** — I found no EORI number for any of the roughly 6 companies I checked. Likely reason: none of these sampled companies import or export physical goods, so an EORI number wouldn't apply to them. Worth trying again specifically on companies that do trade goods internationally. |
| **LEI (Legal Entity Identifier)** | — | **Dead end, confirmed not useful.** LEI numbers are for financial reporting rules; small UK companies almost never have one. Not connected to VAT in practice. |
| **WHOIS** (domain registration lookup) | Who owns a website domain | The one time I needed it (checking if ABC Money Ltd owned abcmoney.co.uk), the owner's details were hidden for privacy — a dead end for proving ownership, though the domain's registration date did help me rule the match out on other grounds. |
| **Known mass-registration / virtual-office addresses** | Not a lookup tool, more of a pattern to notice | Two companies in the sample had this pattern: one shares a registered address known to be used by dozens of unrelated companies (a mass company-formation address in Manchester); the other has a registered address in a typical virtual-office/mail-forwarding format (London, "Office 20566"). This is a useful sign that a company is genuinely small with no real premises — it supports an explanation, but doesn't prove it on its own. |
| **Companies House compliance flags** (overdue accounts or confirmation statement) | An extra signal | Only one company in the sample had both overdue (ABC Money Ltd) — useful as a sign a company may be inactive, but only when combined with other evidence, not alone. |

### Dead ends, explained in detail

The brief asked for dead ends with the exact expectation and the exact reason they failed — not just "scraping doesn't work." Here are the ones I think are worth explaining in detail:

1. **Lord Kitch Management Ltd (13730304) — the clearest trap in the whole sample.** What I expected: a VAT number (GB309240133) kept coming up, at the *exact same registered address* as the target company. What actually happened: HMRC's checker returned the name "LORD KITCH LIMITED" — a real but separate, related company (11644494, property trading) at the same building, not the company I was looking for ("Lord Kitch Management Limited," 13730304, which manages service charges for residents). Google's AI Overview actually merged the two companies into one wrong answer. **The lesson:** matching on address is not the same as matching on identity. You need both the name and the company number to confirm a match. A system that accepts "VAT found at this address" without checking the exact name would have silently recorded the wrong VAT number here.

2. **HTC Consultancy Ltd (10399697).** What I expected: a VAT number found through search. What actually happened: the address linked to that VAT number matched neither the company's registered office (Caistor) nor the director's known address (Petersfield), and there was no ICO registration for it either. CompanyData.com, searching directly by company number, confirmed "not recorded as VAT-registered." I only got this clean, correct "no" result by insisting on matching the exact company number, instead of accepting a search result that just matched on the name.

3. **M A Motors (Leeds) Ltd (08698425) vs. "M. & A. Cars (Leeds) Limited."** A website that looked like a match (mandacarsleeds.co.uk) turned out, on checking, to belong to a *different* company (07291042, registered in Oldham, not Leeds) — same general area, same type of business, a similar but not identical name. I ruled it out instead of assuming it was a match.

4. **Dogstuff Ltd (12555744) vs. dogstuff.co.uk.** A live website exists with a near-identical name, but the company that used to hold that exact name — "Dogstuff.co.uk Limited" (03579024) — was dissolved in 2017, three years before the target company (12555744) was even set up. I couldn't load the live site (it gave a technical error) to check which company, if either, runs it now. I left this as genuinely unresolved rather than guessing.

5. **L.J.V. Consultants Ltd (09712469) vs. several similarly-named consultancies.** I checked two possible websites (ljconsults.com — a US business, no UK company number; ljconsults.co.uk — a UK business, but doing general business-strategy consulting, not the target's "computer facilities management" work, and with no company number shown). Neither was confirmed. Companies House's live website also blocked the AI's automated check on this one.

6. **O'Neill Properties Ltd (NI061938) — two separate false leads for one company.** oneillpr.com turned out to be a company in Texas, USA. oneillproperty.co.uk is a real UK letting agent, but it's registered in Scotland, while my target company is registered in Northern Ireland — a completely different register. I ruled both out. I found no real website for the actual target, which has a very common name.

7. **ABC Money Ltd (11390108) vs. abcmoney.co.uk.** The website says it was founded in 2012 as a financial news publisher, but the actual company was only set up in 2018, in Llanelli, Wales. WHOIS couldn't confirm who owns the site either (the owner's details are hidden). I treated this as a coincidental name match, not a confirmed one — this is supported by the fact that the company's accounts and confirmation statement are both overdue at Companies House, a separate sign it may not be active.

8. **Companies House's live website itself, as a repeated dead end.** This wasn't just one company's problem — it was a problem with the *access channel*. The live, human-facing lookup blocked the AI's automated checks repeatedly (403 errors) in the second half of the sample. I didn't personally hit this problem checking Companies House by hand — Endole was the one that gave me trouble manually, with its own rate limit (see the Endole row above). The bulk data file never had any of these problems. This difference matters enough that it gets its own section in Part 3.

### A note on methodology that belongs here as much as in Part 2

**The SIC code is a weak, last-resort clue — not a rule.** I never treated it as adding real value beyond splitting or filtering the database (for example, to narrow down a testing set, as in "Before the random sample," above) — even two companies with the same SIC code can operate completely differently and won't necessarily have the same VAT situation. Two cases in this sample clearly prove that reasoning based on SIC code alone can be wrong:

- **Cruden Investments Ltd** — SIC code 70100, "Activities of head offices" (a holding company). The usual assumption is that pure holding companies, which don't sell anything directly, are outside VAT rules. What actually happened: it is VAT-registered (GB268991200, confirmed by HMRC), because the group's own terms-and-conditions page names this exact company as making VAT-able sales inside the group.
- **Hextable Care Home Ltd** — SIC code 41100, "Development of building projects," not even a care-sector code, which at first looked like a shell company with no real activity. What actually happened: it is VAT-registered (GB211753536, confirmed by HMRC) — it's the real holding company of the Cinnamon Care Homes Group.

Conclusion: SIC code is fine as a weak first guess about where to look, but it should never be used on its own to decide whether a company "should" have VAT. Every "sector exemption" answer in this project's tracker is backed by independent evidence (a regulator's register, a legal-structure clue, an exact rule in the law) — never the SIC code by itself.

---

## Part 2 — Proof of Concept

### How the sample was chosen

```sql
SELECT TOP 40 *
FROM Veridion
WHERE CompanyStatus = 'Active'
  AND [Accounts.AccountCategory] NOT IN ('DORMANT', 'NO ACCOUNTS FILED')
ORDER BY NEWID()
```

This is a genuinely random sample of *live, active* UK companies — not hand-picked, and specifically **not** chosen to favour companies known to publish their VAT number (the brief warned against this). One thing worth saying plainly: most of the sampled companies are small or very small businesses, because that is what most of the live UK company register actually looks like. If I had picked a sample skewed toward large, well-known companies, the coverage rate would look better than it really is for a dataset covering 40,000 real suppliers.

### How I checked results

Every candidate VAT number — no matter which source gave it to me (Endole, CompanyData.com, a company's own terms-and-conditions page, or another website) — was entered into HMRC's official checker. I compared the name and address HMRC returned against the company's registered office at Companies House. Any mismatch, or "not found," would have been recorded as a false positive. None happened.

When a company had a previous name on record (the bulk data includes this), I also searched under that older name, in case it turned up older information the current name didn't. For National Ecology Consultancy Ltd, for example, I also searched its previous name, "Laws & Co Property Investments Ltd" — but pages like Endole's load under the company's current name regardless, so this didn't surface anything extra in that case. Still, it's a step worth doing when available, since not every source behaves this way.

### Results

| Metric | Value |
|---|---|
| Sample size | 40 |
| **Coverage rate** — a usable VAT number was found | **9 / 40 = 22.5%** |
| VATs confirmed independently by HMRC | 9 / 9 (100% of the VATs found) |
| **False-positive rate** | **0 / 9 = 0%** |
| Website found (confirmed or likely) | 16 / 40 = 40% |
| Website unclear | 3 / 40 |
| No website found | 21 / 40 |

**Coverage rate** = the share of the sample where I actually found and confirmed a VAT number. **False-positive rate** = of the VAT numbers I put forward as a match, the share that turned out — after checking with HMRC — to belong to a different company, or not to exist at all. To measure this properly, I had to test every single candidate, not just the easy, obvious ones. That's what makes the 0% number meaningful, rather than just a result of only checking easy cases.

The 0% doesn't mean I never ran into a wrong VAT number. It means that every time I did, I caught it and rejected it before counting it as confirmed — so it never entered the "9 confirmed" group in the first place. The clearest example is the **Lord Kitch case** (see Part 1, #1): a VAT number at the exact right address, which would have been wrong if I hadn't also checked the name. I rejected it before it could be counted, so it doesn't lower the 0% — but it does show the checking process actually catches real mistakes, not that mistakes never happen.

### Confirmed VAT matches (9)

| Company | VAT | How found | HMRC check |
|---|---|---|---|
| Rachel Anderson Consulting Ltd | GB103354850 | Endole Open | ✅ exact name + address match |
| PAV Fixers Ltd | GB137451515 | Endole Open | ✅ exact match |
| Graham James Lee Ltd (trading as Yellow Door Photography) | GB198427950 | Own site, terms and conditions page | ✅ exact match |
| R W Evans & Son Ltd | GB869464075 | Endole Open | ✅ match (only difference is "Ltd" vs "Limited" — see note below) |
| Caviar Fresh Fish Ltd | GB407333029 | Endole (tied directly to the company number) | ✅ exact match |
| Hextable Care Home Ltd | GB211753536 | Endole | ✅ name matches (address is different — this is because of centralised group VAT registration, not a mismatch) |
| Cruden Investments Ltd | GB268991200 | Own group's terms and conditions page (names the company number and VAT number together) | ✅ exact match |
| Hapsoft Consulting Ltd | GB208341433 | Own site, Legal Notice page (company number and VAT number together) | ✅ exact match |
| Cityfleet Networks Ltd | GB775069400 | vat-lookup.co.uk, also confirmed on Endole | ✅ exact match |

Three lessons about matching that are worth carrying into Part 3, all from real cases, not guesses:
- **Company-name spelling needs to be standardised before comparing.** HMRC returned "R W Evans & Son Ltd," while Companies House has the full legal name "R W Evans & Son Limited." A simple exact-text comparison would wrongly call this "no match," even though it is correct. Any real system needs to treat "Ltd" and "Limited" (and similar short forms) as the same thing before comparing names, or it will wrongly reject correct matches.
- **A different address on the VAT record doesn't automatically mean it's wrong.** Hextable Care Home's HMRC-listed address is different from its Companies House registered office, because it is VAT-registered centrally at its parent group's address — a normal, explainable reason, confirmed by checking the group's structure. This is not a warning sign, unlike the Lord Kitch case, where the *name itself* was wrong.
- **Company numbers need normalising too, not just names.** During earlier testing (see "Before the random sample," above), Vistra Ltd's own terms-and-conditions document wrote its company number as "865285," while Companies House lists it as "00865285," with leading zeros. A strict text match on the company number would have wrongly rejected a genuinely correct result here.

### The other 31 companies: why "not found" isn't one single answer

| Likely explanation | Count | What it means |
|---|---|---|
| Below VAT threshold | 13 | A genuinely small business, likely earning less than the roughly £90k registration threshold |
| Uncertain | 10 | Not enough independent evidence to say anything for sure — a real gap, not a guess |
| Sector exemption | 5 | Falls under a real UK VAT exemption rule (see below) |
| Dormant/shell signal | 3 | Warning signs (overdue filings, no trading activity found, or both) suggest the company isn't really active |

Real exemption categories I confirmed in this sample (under UK VAT law, Schedule 9): **residential care** (Group 7 — Midway Transitional Solutions), **financial and insurance services** (Group 2 — KB Wealth Planning, registered with the FCA), and **burial and cremation services** (Group 8 — CFM Bereavement Services, set up as a company limited by guarantee, which fits a non-profit community organisation). Clearly **not** automatically exempt, even with a similar-looking SIC code: health-related *consultancy* (which is different from actual clinical care — MCQ Healthcare Consultancy), sports services from a normal commercial provider, not a registered non-profit club (Brookesport), and hairdressing (Hewler). Getting this distinction wrong in a real, automated system would wrongly label real "below threshold, might just need chasing" gaps as "expected, don't bother."

One more type of case came up, but I only saw it once, so I didn't count it as its own category above: **cross-border delivery**. ExploreZanzi.com Ltd is a UK-registered company, but the actual service (safari tours) happens entirely in Tanzania, and its own website describes its main office as being in Zanzibar. UK tour operators are usually covered by the Tour Operator's Margin Scheme, under which trips taken outside the UK/EU are zero-rated for VAT — so this company could be VAT-registered with no VAT ever visibly charged, or the real taxable business might actually sit with a separate Tanzanian company, not the UK one. I marked this Uncertain instead of "below threshold," because the cross-border angle is a genuinely different explanation that I only saw this one time. (More on this in "Beyond the UK," below.)

Full detail for every company, including every source I checked and every note above, is in `vat_sample_tracker.csv`.

---

## Part 3 — At Scale

### What this sample tells us about covering 40,000 suppliers

If the 22.5% coverage rate held at a much bigger scale — and there's a real reason to think the true number could be a bit higher, since a real production system would have paid access to Endole/CompanyData.com and could spend more time on the 10 "Uncertain" cases than the 8-10 hours this project allowed — you'd still only be closing a minority of the roughly two-thirds of suppliers (around 26,000 companies) that are currently matched only by name. That's genuinely useful — it meaningfully shrinks the unreliable name-matching problem — but it doesn't replace name-matching. It supports it.

### What breaks first, at scale

1. **Companies House's live website, straight away.** This isn't a guess — it happened repeatedly during this project, in a session with only a handful of requests per company. To be clear about what this source is actually for: the live site never gave VAT numbers or websites, either — the bulk file and the live site both lack those, and the bulk file already has the registered address too (just split across several columns). What the live site adds is *freshness*: catching an address that's changed, or a status/compliance flag, since the last monthly bulk snapshot was taken. At 40,000 companies, sending requests to the live, human-facing lookup without any limits would get blocked almost immediately — so even this smaller, supporting role needs to be slowed down, retried carefully, and queued, or replaced with an official bulk data product for those specific fields, if one exists.
2. **Free third-party sources, next.** Endole Open blocked or paywalled me after fairly light use in a single session, well before I'd even reached 40 lookups. CompanyData.com's free search has no simple web address to call automatically. At 40,000 companies, these stop working without paying for API access (CompanyData.com's paid tier, or a similar company data provider) — which turns this from a "technical scraping problem" into a straightforward cost-per-record question (see below).
3. **Plain web search, or AI-summarised search, by its nature.** This isn't just messy at scale — it actively gives confident wrong answers (the Lord Kitch mix-up). Any system using search results needs a checking step afterward that never fully trusts a search result on its own — search should only produce *candidates*, never *final answers*.
4. **Guessing sector exemptions based on SIC code alone, at the edges.** SIC-based guessing (Part 1) got two clear cases wrong out of 40. At 40,000, that same error rate would wrongly classify thousands of companies as "no VAT expected" if used as a firm rule instead of a weak first guess — costly both in chasing down wrong leads and in wrongly accepting "explained" gaps that are really just below-threshold guesses dressed up as sector reasoning.
5. **Exact-text name and number matching, without any fuzzy logic.** Beyond the "Ltd vs Limited" and "leading zeros" normalisation already covered above, a real system would benefit from proper fuzzy matching (for example, Levenshtein distance, which measures how many single-character edits separate two pieces of text) to catch small typos and formatting differences that a strict, exact comparison would otherwise wrongly reject.
6. **Assuming a source is reliable just because it worked once, from one type of access.** During this project, the AI's automated fetch could reach financialadvisers.co.uk (the site used to confirm KB Wealth Planning Ltd), but when I tried to open the same page myself, in a normal browser, it was blocked outright by the site's own security service (Cloudflare), with a "Sorry, you have been blocked" message. This shows access to the same source can be inconsistent depending on how you reach it, for reasons that have nothing to do with the data itself — a real crawling system at scale needs to expect and handle this, not assume that "it worked once" means "it will keep working."

### Cost per company (rough estimate)

These are broad categories, not exact prices:
- **Free open-web approach (what this project used):** no direct money cost, but a very high *time* cost per company (checking several sources by hand, several minutes each for the unclear cases). Dividing the ~10 hours spent by the 40 companies gives a rough average of 15-20 minutes each — this is a back-of-envelope number, not something I timed company by company, and it was pulled up by the "Uncertain" cases taking much longer than the confirmed ones, and by the fact that the method itself was being worked out along the way, not already known from the start. A researcher who already knew the approach and tools going in would likely be faster per company. Either way, this pace does not scale to 40,000 companies without either a large team of people doing this by hand, or automation — and automation runs straight into the rate-limit problem above.
- **A paid company-data API** (for example, CompanyData.com's paid tier, or a similar bulk data provider) — a cost per lookup, likely low cents to a few dollars per company depending on the deal, but its coverage is limited by *what that provider itself was able to find* — which is really the same open-web-plus-HMRC problem, just one step removed. You're paying to outsource this exact same difficulty, not to remove it.
- **Paying people to review the "Uncertain" cases specifically** — this is where real money should go, rather than spreading it evenly. The 10 "Uncertain" cases in this sample weren't unsolvable — they were simply not given enough resources (a paid Companies House account, a phone call, or a paid people/company-search tool would likely solve most of them). Spending money on people specifically for this group, rather than spreading it across all 40,000 records evenly, is the efficient way to spend it.

### What stays reliable, and what needs constant attention

The bulk Companies House file is cheap and reliable to refresh every month. Checking a VAT number with HMRC, when you already have a candidate number, is free and reliable per check, within its rate limits and the new requirement to give your own VAT number. Everything else — Endole, other websites, general search — either needs a paid contract, or you need to accept that it gets worse as you use it more.

### Watching the system once it's running

Since there's no complete, trusted dataset to compare against (this is also debate topic 3, below), monitoring has to work indirectly:
- **Track the failure rate of checks over time.** If the share of candidate VAT numbers that fail the HMRC check starts rising, something has gone wrong with a source (stale data, a broken scraper, a new kind of naming trap) — even if you can't say exactly which records are now wrong.
- **Track the coverage rate by sector and company size, as a spread of numbers, not just one overall figure.** A sudden drop in coverage for a group that used to match well is an early warning sign that something broke, well before anyone notices individual wrong matches.
- **Re-check confirmed records on a regular schedule, not just once.** VAT registration status really does change over time (companies register, deregister, or close — see debate topic 2) — so a "confirmed" record needs a date attached, and should expire, rather than staying marked as true forever.
- **Keep a log of rejected candidates, not just accepted ones.** Recording *why* a candidate was rejected (a Lord Kitch-style name mismatch, genuinely not found, or the source being unavailable) lets you notice a new pattern of failures, instead of discovering the same problem again and again, one company at a time.

---

## Debate Topics

### 1. VAT numbers are 9 digits plus a checksum — is it a good idea to guess numbers against HMRC's checker?

This is more technically possible than it sounds (9 digits gives about a billion combinations, and the checksum rule is public, so you could narrow it down to only the numbers that pass the checksum first — a much smaller set of possibilities). But I don't think it's a good idea, for reasons beyond just "it's a lot of requests":

- It answers the wrong question. HMRC's checker confirms that *a specific number belongs to a specific business* — guessing numbers would, at best, tell you a number is *valid and belongs to somebody*, with no way to know which of your 40,000 target companies it belongs to. You would still need to match the name and address to your target company, so you haven't actually solved the real problem — you've just created a huge list of valid but unmatched numbers to sort through afterward.
- You would almost certainly get blocked long before checking a meaningful share of all possible numbers (the checker already showed friction with normal, single requests in this project). Doing this anyway looks a lot like misusing a government service, not a legitimate way to collect data — a real risk to a company's reputation, and possibly a legal one too.
- Many numbers that pass the checksum test don't belong to any real, registered business (they may be deregistered, never issued, or set aside for future use) — so even a "successful" attempt at guessing would give you a lot of dead numbers mixed in with real ones, and the checker won't tell you which is which beyond a simple pass or fail.

My conclusion: interesting as a "could this technically work" question, but the wrong tool for this job. The real challenge is knowing *whose* number it is, not finding *which* numbers exist.

### 2. Keeping the dataset up to date

The clearest example from this sample: **Crunch (West Bridgford) Ltd** is still listed as "Active" on Companies House, with no overdue filings, but the actual shop closed in August 2025, according to local news. The bulk file's "live" status was already out of date compared to reality by the time I checked it. Companies register and deregister for VAT on their own schedule, completely separate from their Companies House filing schedule (which can lag by up to a year, even for a fully compliant company).

In practice, this means:
- Every VAT record should be treated as **having a date, and losing reliability over time** — not as permanently true. Re-check it on a schedule that matches how likely that type of company is to change (small companies more often, large stable ones less often).
- Use **compliance events as a trigger to re-check**, instead of a fixed calendar schedule — a new confirmation statement or set of accounts is a natural moment to re-check VAT status, because it's a moment the company is already updating its own official record anyway.
- Accept that **some out-of-date information is unavoidable, and this should be shown clearly, not hidden.** A "last checked on" date on every record lets the people using it (the procurement team) judge for themselves how much to trust an older match, instead of treating a two-year-old check the same as one done today.

### 3. How would you know the dataset is wrong at scale, with nothing complete to compare it against?

The same discipline this project used is the template here, just applied more broadly. You can't check every record against a complete, trusted reference, because none exists — but you can build **internal checks that don't need one:**

- **How often independent sources agree.** When two separate sources (for example, Endole and a company's own website) both give the same VAT number for the same company, that's much stronger evidence than either alone. Track what share of "confirmed" records only have one source behind them, and treat those as lower-confidence by default.
- **Checksum and format checks as a minimum bar, not the whole answer.** Easy to automate, and catches typing mistakes — but proves nothing about whether the number actually belongs to the right company. Necessary, but nowhere near enough on its own.
- **Regularly re-checking a random sample by hand, not just once.** This is exactly what Part 2 of this project did — take a random sample of "confirmed" records on an ongoing basis and manually run them through HMRC's checker again. If the false-positive rate found this way ever moves above zero, something in the pipeline has gone wrong, and you'll know roughly when, even without knowing exactly which records are bad.
- **Watching for patterns in rejected candidates, not just accepted ones** (see the monitoring section in Part 3). A sudden rise in one type of failure (for example, "name doesn't match at the same address") is itself a warning sign — maybe a new kind of naming trap, or a source that has started giving stale or wrong data.
- **Using results further downstream as an indirect signal.** If the procurement team's actual invoice-matching accuracy gets better after using this VAT dataset, that's evidence the dataset is helping overall, even without knowing its exact error rate. If it doesn't improve, or gets worse, that's a strong reason to investigate, even with no labelled data telling you exactly which records are wrong.

None of these on its own proves everything is correct. Together, they limit the risk — which is the honest limit of what's possible without a complete reference dataset.

### 4. Which sources would you NOT be comfortable using in a product you sell to customers, and why?

Specifically: **general open-web search of a person's name.** Several sampled companies are really just one person's business under their own name (Paul Walker ECI Ltd, E R Murfin Ltd) — the director's surname is the company name. Searching for these brings up unrelated people with the same name (I hit this immediately with real actors, other businesses, and unrelated professionals on LinkedIn), and goes beyond a legitimate company lookup into researching a private person's life, using information they never chose to connect to their business.

I deliberately stopped short of this for E R Murfin Ltd — company-number-only searches came up empty, and going further wasn't a fair trade-off for finding just a VAT number.

The practical line I'd draw for a sold product: **only structured, business-focused sources** are acceptable (company number or exact registered name, through Companies House, HMRC, or a sector regulator's register). **Free-text search of a person's name** is not, no matter how small the company is. A production system should treat "no business-record source found this" as an acceptable final answer — an Uncertain, or a gap — not a trigger to search further into someone's life.

I would also flag **other websites that collect VAT data from unclear sources** (sites like vat-lookup.co.uk) as something I wouldn't want to rely on *as a main source* in a sold product — not for privacy reasons, but because I have no way to check where their data comes from or how current it is, and this project caught one of them directly contributing to what would have been a false positive (the Lord Kitch case). Fine as a way to find leads that then get checked properly through HMRC — not something I'd want a paying customer's data quality to depend on unchecked.

---

## Beyond the UK

Most of my time went into learning the SQL side of this project as a beginner, and into understanding each step of the research myself — including Claude's part in it — rather than just accepting results. So I'd rather leave this section out than write a comparison built on sources I hadn't checked myself, the same standard I held everywhere else in this project. The one real cross-border detail that did come up naturally from the UK sample — ExploreZanzi.com Ltd (#28), a UK-registered company whose actual service happens entirely in Tanzania — is already covered in its row in `vat_sample_tracker.csv`, and in the "why not found isn't one single answer" section of Part 2 above.

---

## Supporting code

The `code/` folder has three small, simple scripts, with no extra software needed to run them:

- **`01_sample_query.sql`** — the exact SQL Server query used to pick the 40-company random sample, with comments explaining the reason for each condition in the query.
- **`02_vat_checksum_validator.py`** — checks whether a UK VAT number passes HMRC's Mod 97 / Mod 9755 checksum rules (the standard 9-digit format). Run it with no arguments and it checks itself against the 9 VAT numbers this project actually confirmed with HMRC (all of them pass). You can also give it other VAT numbers to check. This is deliberately built only as a *first, rough filter* — see the notes in the script itself, and debate topic 1, for why passing this check is never treated as proof the number is correct or belongs to the right company.
- **`03_compute_sample_stats.py`** — recalculates every main number in Part 2 (coverage rate, false-positive rate, the breakdown of "no VAT" explanations) directly from `vat_sample_tracker.csv`. It also includes a check that would have caught, automatically, the CSV formatting mistake this project actually ran into partway through (a comma inside one field, without quotes, silently shifted later columns out of place in 3 of the 40 rows) before it could affect any reported number. You can run it yourself with: `python3 code/03_compute_sample_stats.py vat_sample_tracker.csv` — its output matches the table in Part 2 exactly.

---

## Files in this submission

- `README.md` — this document
- `vat_sample_tracker.csv` — full detail for all 40 sampled companies: website found, VAT found, VAT number, HMRC check result, likely explanation, confidence level, and full notes on sources for every row
- `code/01_sample_query.sql`, `code/02_vat_checksum_validator.py`, `code/03_compute_sample_stats.py` — supporting code (see "Supporting code" above)
