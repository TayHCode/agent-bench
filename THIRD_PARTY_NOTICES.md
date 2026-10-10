# Third-party notices

The runner is MIT, copyright TayHCode. Each bundled task retains its full source license. Required upstream copyright holders and public source URLs remain as legal attribution; owner and machine identity are not attribution.

## fda-recalls-clean

Source: https://api.fda.gov/food/enforcement.json?search=report_date:[20260701+TO+20261008]&limit=1000. License: CC0-1.0 (openFDA, https://open.fda.gov/license/). Full terms: [fda-recalls-clean/LICENSE-SOURCE](tasks/fda-recalls-clean/LICENSE-SOURCE).

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## humanize-intcomma-overflow

Source: https://github.com/python-humanize/humanize/pull/392. License: MIT. Full terms: [humanize-intcomma-overflow/LICENSE-SOURCE](tasks/humanize-intcomma-overflow/LICENSE-SOURCE).

Attribution: Copyright (c) 2010-2020 Jason Moiron and Contributors.

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## irs-donee-matching

Source: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf. License: public domain (US government work, 17 U.S.C. 105). Full terms: [irs-donee-matching/LICENSE-SOURCE](tasks/irs-donee-matching/LICENSE-SOURCE).

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## mypy-deferred-alias-crash

Source: https://github.com/python/mypy/pull/22096. License: MIT. Full terms: [mypy-deferred-alias-crash/LICENSE-SOURCE](tasks/mypy-deferred-alias-crash/LICENSE-SOURCE).

Attribution: Copyright 2012–2023 Jukka Lehtosalo and contributors; 2015–2023 Dropbox, Inc.

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## taskiq-lazy-logging

Source: https://github.com/taskiq-python/taskiq/pull/665. License: MIT. Full terms: [taskiq-lazy-logging/LICENSE-SOURCE](tasks/taskiq-lazy-logging/LICENSE-SOURCE).

Attribution: Copyright (c) 2022-2023 Pavel Kirilin.

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## werkzeug-apply-conditions

Source: https://github.com/pallets/werkzeug/pull/3308. License: BSD-3-Clause. Full terms: [werkzeug-apply-conditions/LICENSE-SOURCE](tasks/werkzeug-apply-conditions/LICENSE-SOURCE).

Attribution: Copyright 2007 Pallets. BSD-3-Clause requires retaining the copyright, conditions and disclaimer in source distributions and reproducing them in documentation or other materials for binary distributions. The full notice is retained in LICENSE-SOURCE.

The manifest identifies base and fix commits, original modifications and authorship-review limitations. Code snapshots are supplied by pinned recipes; bundled data labels are generalized consistently where they overlap private terms.

## Additional bundled licenses

Historical licence files for removed source trees remain at their original paths, including Scrapy's BSD-3-Clause notice (copyright Scrapy developers; https://github.com/scrapy/scrapy). These licence-only directories are not runnable tasks or bundled source snapshots.

Prepared mypy sources bundle typeshed under Apache-2.0; the pinned upstream archive includes its full notice and Python/PSF-related terms. Source archives are downloaded only by explicit task preparation. Mypy's LICENSE-SOURCE also retains the original auxiliary permissive notices although mypyc is omitted. This export ships no full upstream source snapshots or artwork: reconstruction downloads the original public sources and preserves their notices.

## Omitted pilot and synthetic fixtures

One pilot task from a third-party library was removed to keep the licence trail clean. Its source, hidden checks, gold and mandatory notices are absent from this clean-history export; historical measured rows use the generic `removed-pilot-task` label. The synthetic median task moved to `tests/fixtures/`; it is not an upstream human gold fix and is excluded from the benchmark pool. It and the toy demonstration are original MIT test scaffolding, copyright TayHCode.

FDA: the food-enforcement fields used here are public domain / CC0 under https://open.fda.gov/license/ ; no GMDN medical-device terminology is included. IRS: federal employee-created records may be copied under https://www.irs.gov/about-irs/use-of-content-from-irsgov ; attribution is to the U.S. Internal Revenue Service, under 17 U.S.C. 105. No agency endorsement is implied.

## pydantic-namespace-inspection

Source: https://github.com/pydantic/pydantic/pull/13596. MIT, Copyright (c) 2017 to present Pydantic Services Inc. and individual contributors. Full unmodified notice: [LICENSE-SOURCE](tasks/pydantic-namespace-inspection/LICENSE-SOURCE). The unchanged bundled pydantic-core source is also MIT, Copyright (c) 2022 Samuel Colvin; its full original notice is appended to the same LICENSE-SOURCE and retained in the prepared tree. Source, PR tests and gold are fetched only on explicit preparation.

## mypy-paramspec-unpack-crash

Source: https://github.com/python/mypy/pull/22123 (report #21778). MIT; Copyright 2012–2023 Jukka Lehtosalo and contributors; 2015–2023 Dropbox, Inc. Full unmodified upstream notice and auxiliary notices: [LICENSE-SOURCE](tasks/mypy-paramspec-unpack-crash/LICENSE-SOURCE). Prepared sources preserve typeshed notices. Source, PR tests and gold are fetched only on explicit preparation.

## qcew-county-shift-share

Source: U.S. Bureau of Labor Statistics QCEW, https://www.bls.gov/cew/downloadable-data-files.htm, first-quarter 2026 release dated 2026-08-28. Data are public domain (17 U.S.C. 105). The original BLS public-domain terms are retained in [LICENSE-SOURCE](tasks/qcew-county-shift-share/LICENSE-SOURCE). No photographs, illustrations or emblem are included. Unchanged checksum-pinned archives and known answers are created outside the shipped tree only by explicit `agentbench task prepare`.
