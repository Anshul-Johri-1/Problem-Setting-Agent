# Polygon API — §18 Verification Findings

Status of each build-checklist item from the spec (§18). **All items verified
live against `anshul_johri`'s account on 2026-07-11.**

| # | Item (§ref) | Status | Finding |
|---|---|---|---|
| 1 | Request-signing recipe (§9.1) | ✅ **Confirmed LIVE** | `apiSig = <rand> + sha512hex("<rand>/<method>?<sorted_params>#<secret>")`. Params sorted lexicographically **by name**; include `apiKey`+`time`, exclude `apiSig`. Hash over **raw** values; POST body URL-encoded; POST `application/x-www-form-urlencoded` to `https://polygon.codeforces.com/api/<method>`. Live `problem.create` accepted our signature. |
| 2 | Invocations API (§9.4) | ✅ **Confirmed NOT exposed** | All candidate methods (`problem.startInvocation`, `.invocations`, `.runInvocation`, `.solutionsInvocations`, `.verdicts`) return **HTTP 404**. No judge-side API. Matches polyman (judges locally). → use the abstract interface in `invocations.py`; default to `local_harness`. |
| 3 | Access-granting API (§9.5) | ✅ **Confirmed NOT exposed** | All candidates (`problem.addUser`, `.saveAccess`, `.grantAccess`, `.setAccess`, `.access`) return **HTTP 404**. The one manual step stands (§16/§17). `access.py` reminder is correct. |
| 4 | Standard-checker filenames (§14) | ✅ **Confirmed LIVE** | `setChecker` accepts the `std::<name>.cpp` form. **Accepted:** `std::wcmp.cpp`, `std::ncmp.cpp`, `std::rcmp4.cpp`, `std::rcmp6.cpp`, `std::rcmp9.cpp`, `std::yesno.cpp`, `std::nyesno.cpp`, `std::lcmp.cpp`, `std::fcmp.cpp`, `std::hcmp.cpp`. **Rejected:** `std::acmp.cpp` (does not exist), bare `wcmp.cpp` (must have `std::` prefix). → `config/standard_checkers.yaml` should use exactly these names. |
| 5 | `/p/<owner>/<name>` URL (§16) | ✅ **Pattern confirmed** | The route returns **HTTP 401 (auth required)**, not 404 — the pattern is valid; it renders once logged in. Constructed from `problem.create`'s `owner`+`name` (see #6 correction). |
| 6 | saveScript/saveTest model (§18) | ✅ **Confirmed LIVE** | Polygon script lines MUST end with `> <testIndex>` and reference generators by name, e.g. `gen_random -n 50 -seed 1 > 3`. Manual `saveTest` and script tests share the test-index space (samples 1..k, script tests k+1..). Confirmed via a full pipeline upload. |

## ⚠️ Spec correction discovered live (§16)

**`problem.info` does NOT return `owner` or `name`.** Live response is only:
`{timeLimit, memoryLimit, inputFile, outputFile, interactive, wellFormed}`.

Owner + name come from the **`problem.create`** result instead:
`{id, owner, name, deleted, favourite, accessType, revision, modified}`.

Also: **`owner` is returned lowercased** (`anshul_johri`, not `Anshul_Johri`).
Link construction must use the create-result owner verbatim, not `problem.info`
and not the mixed-case `.env` handle. Implemented in `methods.problem_url`.

Other live-confirmed rules:
- Problem **name** must match `[a-z0-9-]+` (underscores rejected — dashes only).
- `buildPackage` requires **exactly one main (`MA`) solution** to exist first;
  calling it earlier fails with "Expected to find exactly one main (model)
  solution" (method works, precondition enforced).
- `commitChanges`, `packages`, `updateWorkingCopy`, `setChecker` all work live.

Live-confirmed rules discovered building the full pipeline (2026-07-11):
- **Script format**: each `saveScript` line must end `> <testIndex>` (§18 #6).
- **Solution base names must be unique ignoring extension** — `correct.cpp` and
  `correct.py` collide ("file with the same name (without extension)"). The
  pipeline disambiguates on upload (`correct.py` → `correct_py.py`) while keeping
  local filenames.
- **timeLimit floor is 250ms** (`updateInfo` rejects lower). Local harness may
  use a tighter limit for brute separation; upload clamps to ≥250.
- **Solution tags are strictly enforced at package build.** A solution tagged
  `RE` that gets `TL` fails the build ("violates tag(s)"). Tags must match actual
  verdicts; a solution with mixed failing verdicts must use `RJ` (generic
  rejected), not a specific verdict tag. The pipeline now derives tags from the
  local verdict matrix (mixed → `RJ`) so uploads always satisfy this.
- `problem.packages[].comment` carries the build failure reason — use it for
  diagnostics (there is no separate log method).
- **`problem.saveValidatorTest`** works (`testIndex`, `testInput`,
  `testVerdict` ∈ VALID/INVALID). BUT Polygon **trims the trailing newline** on
  manually-saved validator-test inputs, so a strict validator rejects a `VALID`
  manual test → package build fails ("Validator test #N got INVALID, but VALID
  expected"). Fix: upload only the malformed `INVALID` corpus as validator tests
  (rejection is expected regardless of trimming); the real generator-produced
  test set is validated during the build anyway, so valid-input coverage isn't
  lost. Empty `testInput` is also rejected — keep empty cases local-only.
- Package build with `verify=true` **strictly enforces solution tags** end to
  end (ran the full divsub roster: MA→OK, brute→TL, WA1–4→WA all matched).

## Decisions locked in this slice

- **Hand-rolled Python** API layer (not polyman/TS): one Python codebase; live
  signing verification was the point. polyman noted in README as alternative.
- **Invocations** → abstract interface (`invocations.py`), `LocalHarnessInvocations`
  default backend, browser backend reserved. Orchestrator stays backend-agnostic.
- **Access** → no-op reminder (`access.py`), the one manual step.

## ✅ End-to-end upload path — verified LIVE (2026-07-11)

`scripts/e2e_dry_run.py` built a complete `a+b` problem and Polygon reported the
package **`READY` with `verify=True`** — i.e. server-side it compiled the testlib
validator + ran it against all tests, compiled & ran the `MA` solution to
generate answers, and applied the `std::ncmp.cpp` checker, all passing.

Confirmed-working full sequence (each a single API call, all first-try):
`create → updateWorkingCopy → saveStatement (LaTeX ok) → saveFile(validator.cpp,
type=source) → setValidator → setChecker(std::ncmp.cpp) → saveSolution(main.cpp,
tag=MA) → saveTest ×2 → commitChanges → buildPackage(full,verify) →
packages (poll state RUNNING→READY)`.

Notes:
- `saveTest` manual-test path confirmed (§18 #6 partially — `saveScript`+generator
  path still to be exercised in the generator slice).
- Package build is async; poll `problem.packages`, newest has `state ∈
  {PENDING, RUNNING, READY, FAILED}`. READY took ~40s here.
- Validator/checker sources upload via `saveFile(type='source')`; Polygon
  compiled the testlib validator with no `sourceType` hint needed.

## Throwaway problems left on the account (no delete API)

- id **559169** (`probe-1783710128`)
- id **559171** (`probe-info-1783710183`)
- id **559172** (`e2e-aplusb-1783710477`) — the full E2E problem; has a clean
  built package. Keep as a reference or delete from the UI.

Remove from the Polygon UI when convenient.

## polyman method enumeration (reference)

Confirmed-present (subset relevant to us): `problem.create, .info, .updateInfo,
.updateWorkingCopy, .discardWorkingCopy, .commitChanges, .saveStatement,
.saveFile, .setValidator, .setChecker, .setInteractor, .saveSolution,
.solutions, .saveScript, .saveTest, .tests, .testInput, .testAnswer, .saveTags,
.buildPackage, .packages, .package`. **Absent:** invocations/verdicts, access.
