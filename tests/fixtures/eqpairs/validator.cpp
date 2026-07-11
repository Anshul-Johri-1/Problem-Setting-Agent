// eqpairs validator. Multitest: t, then per test: n, then n integers.
//
// Uses readFinalEoln() ONLY for the very last line of the file (before the
// trailing inf.readEof()), not for every line: registerValidation() sets
// strict mode, under which readEoln() requires a literal '\n' and does NOT
// accept true EOF as a substitute — Polygon's saveValidatorTest trims the
// trailing newline off manually-uploaded Validator-tab tests, so a bare
// readEoln() on the truly-last line would reject an otherwise-valid test the
// moment it's uploaded. The guard checks inf.eof(), NOT inf.seekEof():
// seekEof() calls skipBlanks() first, which would also silently swallow a
// stray trailing space or extra blank line that should be rejected. Plain
// eof() reports true only when literally nothing remains, so it tolerates
// exactly a missing final newline and nothing more. It's also only safe at
// the true end of input — used at any intermediate line break it would (via
// its own false-return) correctly leave the strict readEoln() in place, but
// there's no reason to pay for the check there. See tutorials/validator.md.
#include "testlib.h"

static inline void readFinalEoln() {
    if (!inf.eof()) inf.readEoln();
}

int main(int argc, char* argv[]) {
    registerValidation(argc, argv);
    int t = inf.readInt(1, 10, "t");
    inf.readEoln();  // plain: more content always follows
    for (int tc = 1; tc <= t; ++tc) {
        setTestCase(tc);
        int n = inf.readInt(1, 100000, "n");
        inf.readEoln();  // plain: the values line always follows
        for (int i = 0; i < n; ++i) {
            inf.readInt(1, 1000000000, "a_i");
            if (i + 1 < n) inf.readSpace();
        }
        // Only the LAST line of the LAST test case is the true end of file.
        if (tc < t) inf.readEoln();
        else readFinalEoln();
    }
    inf.readEof();
    return 0;
}
