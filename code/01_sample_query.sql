-- ============================================================================
-- Draws the 40-company random sample used for the Part 2 proof-of-concept.
-- Run against a SQL Server database containing the Companies House
-- "Free Company Data Product" bulk snapshot, imported into a table
-- named `Veridion` (one row per UK company).
--
-- Design choices, made deliberately (see README Part 2 for the full case):
--   - CompanyStatus = 'Active' only: we're sampling the live company
--     population a real procurement dataset would need to match against,
--     not dissolved/historical companies.
--   - Excludes DORMANT / NO ACCOUNTS FILED accounts categories: the brief
--     explicitly warned against cherry-picking companies known to publish
--     VAT, but sampling in obviously-dormant shells would bias the sample
--     the other way (toward companies that were never going to have VAT
--     for reasons unrelated to discoverability). This still leaves plenty
--     of small/micro companies in-sample, which is realistic, not a flaw.
--   - ORDER BY NEWID(): genuine random ordering in SQL Server, re-run
--     gives a different sample each time (not seeded/reproducible by
--     design, since the goal was an honest random draw, not a fixed
--     regression-test sample).
-- ============================================================================

SELECT TOP 40 *
FROM Veridion
WHERE CompanyStatus = 'Active'
  AND [Accounts.AccountCategory] NOT IN ('DORMANT', 'NO ACCOUNTS FILED')
ORDER BY NEWID();
