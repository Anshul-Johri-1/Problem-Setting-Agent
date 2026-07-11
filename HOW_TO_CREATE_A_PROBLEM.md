# How to Create a Problem

This is a guide for problem setters using the agent to create Codeforces
Polygon problems. It describes what to type and what to expect — no repo
internals required.

## One-time setup

1. Clone this repo.
2. Copy `.env.example` to `.env` and fill in your own Polygon API key/secret
   (Settings → API on Polygon) and your Polygon handle. This is a one-time,
   per-person step — problems you create belong to your own account.
3. Open the repo in Claude Code (or your AI tool of choice).

You're ready to create problems.

## Step 1 — Describe the problem

Type `/create-problem` followed by these fields:

```
/create-problem
name:          carrot-sum
statement:     Count integers in [L, R] whose digit sum is prime and
               the number is divisible by that digit sum.
solution:      Digit DP — precompute suffix-count tables per prime
               digit-sum (≤162), process queries offline.
constraints:   1 ≤ t ≤ 10^4, 1 ≤ L ≤ R ≤ 10^18
time_limit:    2s          (optional — the agent proposes one if you skip this)
memory_limit:  256mb       (optional)
answer_unique: yes         (optional — the agent infers this if you skip it)
sample tests:
  Input:  3
          1 10
          12 12
          1 100
  Output: 4
          1
          10
```

**Required:** `name`, `statement`, `solution`, `constraints`, `sample tests`.
Everything else is optional — the agent will propose sensible values and show
its reasoning for you to review.

A couple of things worth knowing:
- `name` must be lowercase letters, digits, and dashes only (e.g.
  `carrot-sum`, not `carrot_sum`) — that's a Polygon requirement.
- Write `statement` and `solution` in plain prose. You don't need to write the
  final problem statement yourself — the agent will draft that.

## Step 2 — Review the spec, then approve

The agent will come back with a `PROBLEM_SPEC.md` — a one-page summary of the
whole problem: the drafted statement, constraints table, proposed time/memory
limits (with reasoning), which checker it plans to use and why, the test-tier
plan (how it intends to separate a correct solution from a slower one), a
preview of the solution files it will write, and any open questions it wants
you to weigh in on.

**This is the one point where the agent stops and waits for you.** It will
not generate any files, write any code, or touch Polygon until you respond.

Read it and do one of:

- **Reply `approved`** — the agent proceeds fully on its own from here:
  writing the statement, validator, checker, generators, and solutions;
  testing everything locally; uploading to Polygon tab by tab with a commit
  per tab; running the test suite; and building the final package.

- **Ask for changes** — just describe what's wrong or what you'd like
  different ("the time limit seems tight, bump it to 3s", "I actually want
  the answer to allow multiple valid outputs", etc.). The agent will revise
  the spec and show it to you again. Repeat as many times as you like — there's
  no limit on revision rounds.

Nothing after your approval requires further input from you, unless something
goes wrong (see below).

## Step 3 — Get your link

Once everything passes, you'll get a message like:

```
✅ Problem ready: carrot-sum

Polygon:     https://polygon.codeforces.com/p/your_handle/carrot-sum
Revision:    7 commits (statement → validator → checker → tests →
             solutions → limits → final), package built clean
Checker:     standard: wcmp
Solutions:   8 files
Tests:       13 files, built from 3 generators
Invocations: clean — all solutions behaved as expected

⚠️  One step left for you: add `newton_school` as a WRITE
    collaborator on the problem page (Add Users tab) — Polygon
    doesn't expose access grants via API, so this has to be done
    by hand.
```

Click the link to see your problem on Polygon. The one manual step — granting
`newton_school` access — is the only thing Polygon doesn't let the agent do
for you; everything else is already done.

## If something goes wrong

Occasionally the agent will stop partway through and hand you a diagnostic
report instead of a link — for example, if one of its "correct" solutions
unexpectedly fails a test. This isn't something the agent will try to
silently patch around, because it usually means there's a genuine ambiguity
in the problem statement or constraints that only you can resolve. Read the
report, decide how you'd like it resolved, and let the agent know — it'll
pick up from there.

## Tips

- You don't need to specify test sizes, generator logic, or which bugs the
  wrong-answer solutions should contain — the agent designs all of that from
  your `constraints` and `solution` fields.
- If you already know you want a custom checker (e.g. "print any valid
  answer"), just say so in `answer_unique: no` — otherwise the agent defaults
  to a standard checker.
- The more precise your `solution` field is (algorithm + complexity), the
  better the agent's test design will be — it uses this to compute exactly
  how large a test needs to be to separate your intended solution from a
  slower brute-force one.
