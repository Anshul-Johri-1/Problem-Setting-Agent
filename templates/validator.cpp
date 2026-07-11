// Validator template (testlib.h). Validate t-bounds AND per-test-case bounds
// separately (§8.3). Reject trailing whitespace, extra tokens, wrong counts,
// out-of-range values, missing EOF/EOLN. Read every value with a range.
//
// IMPORTANT — the very last `inf.readEoln()` in the file (i.e. the one right
// before the trailing `inf.readEof()`) must use `readFinalEoln()` below
// instead of a bare call. registerValidation() sets strict=true, under which
// readEoln() requires a literal '\n' and does NOT accept true EOF as a
// substitute. Polygon's problem.saveValidatorTest trims the trailing newline
// off any manually-saved Validator-tab test, so a validator that requires one
// on its last line will spuriously reject an otherwise-valid test the moment
// it's uploaded that way.
//
// Do NOT use this guard anywhere else, and note it checks inf.eof(), NOT
// inf.seekEof(): seekEof() calls skipBlanks() first, which would also silently
// swallow a stray trailing space or extra blank line that SHOULD be rejected.
// Plain eof() reports true only when literally nothing (not even whitespace)
// remains, so it tolerates exactly one thing — a missing final newline — and
// nothing else. It's also only safe at the true end of the file: mid-file,
// eof() correctly returns false and a normal strict readEoln() still runs.
#include "testlib.h"

static inline void readFinalEoln() {
    if (!inf.eof()) inf.readEoln();
}

int main(int argc, char* argv[]) {
    registerValidation(argc, argv);

    // --- multitest header ---
    int t = inf.readInt(1, 10000, "t");
    inf.readEoln();  // plain: more content always follows

    for (int tc = 1; tc <= t; ++tc) {
        setTestCase(tc);
        // TODO: read this test case's tokens with explicit ranges, e.g.
        // int n = inf.readInt(1, 100000, "n");
        // inf.readSpace();
        // long long x = inf.readLong(1, 1000000000000000000LL, "x");

        // Only the LAST line of the LAST test case is the true end of file.
        if (tc < t) inf.readEoln();
        else readFinalEoln();
    }

    inf.readEof();
    return 0;
}
