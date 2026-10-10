# M5 acceptance record

Three new candidates use original public sources after 2026-06-30. Code fixes
were screened via PR author, body, labels, every PR commit message and squash
merge, plus public comments/reviews. No undisclosed AI use can be ruled out.

- Pydantic #13596, merged 2026-08-06: 399 changed source lines across three modules,
  human author Viicos, two commits without model trailers. Four complete upstream
  test files come from the fix commit. The base fails six tests; real gold passes
  all 374 applicable tests twice. The bundled core at that exact revision is built
  before timing because the same-version published wheel lacks an unrelated fix.
- mypy #22123, merged 2026-10-08, report #21778 opened 2026-07-27: 423 changed source
  lines across two modules. Human author ilevkivskyi, one commit without model
  trailers. The final traceback frame is TypeVarTuple expansion; parameter-list
  normalization is the missing upstream behavior. One complete updated PR suite
  and six neighboring suites run: base fails its regression, gold passes 1,294
  cases twice. The probe's attempted fix fails the upstream check.
- BLS QCEW first-quarter release 2026-08-28: original 2025/2026 singlefile ZIPs,
  downloaded 2026-10-10 and checksum-pinned. Exact-rational known answers cover
  58,712 county-sector rows and 3,143 county rows. An independent DuckDB SQL
  implementation agrees on every cell. Absent deliverables fail and gold passes
  twice. The release CLI now invokes the checksum-pinned data preparer.

Sonnet 5.5 / Claude Code / medium effort, one fresh run per candidate, with
300,000 fresh tokens, 20 minutes and $1.50 ceilings. Dependency setup and hidden
checks are outside the measured agent time. Only probes count toward the $3 job
budget. Each manifest records its completed probe's time, check outcome, cost and
retention reason. Raw sessions and working copies stay outside shipping files.

Rejected during provenance screening (no paid probe): SymPy #30180 disclosed
Fable/Claude-written commits; SymPy #30540 disclosed model-generated code/tests;
NetworkX #8900 disclosed AI assistance, so it was conservatively excluded.
No task was made harder by corrupting data, inserting a synthetic bug, dropping
needed dependencies, or restricting tools. The original selection policy replaced successful probes below four minutes.
For this release, an under-four-minute pass would instead be labelled medium;
tasks are never weakened or hardened to preserve a difficulty label. Valid failed
checks qualify under the requested rule irrespective of elapsed time. There is no full contestant matrix.

Code-task probes (completed, effort verified, no peek detected, hidden check failed):

- mypy-paramspec-unpack-crash: 97.7 seconds (1.63 minutes), $0.18651, 29586 fresh tokens.
- pydantic-namespace-inspection: 29.1 seconds (0.49 minutes), $0.10344, 16749 fresh tokens.
- The earlier QCEW run (81.5 seconds, $0.12195) is invalid difficulty evidence
  because required deliverables were missing; it is superseded, not a hard-task qualification.
- Fresh input-verified QCEW replacement: 143.8 seconds (2.40 minutes), $0.20273, 28719 fresh tokens.
  Both deliverables exist but their complete keysets fail. See
  [QCEW acceptance](../qcew-county-shift-share/ACCEPTANCE.md).

Earlier selection spend was $0.41190, including the excluded QCEW run. This
release spent $0.20273 on exactly one replacement (cumulative selection spend
$0.61463); no full matrix ran. Valid failures retain these as hard
candidates; these n=1 probes do not demonstrate a 10–30 minute successful solve.
