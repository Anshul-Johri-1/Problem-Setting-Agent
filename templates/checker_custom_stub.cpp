// Custom checker template (testlib.h). ONLY used when the answer is not unique
// (§14). Use readAns (jury answer) and readOuf (contestant output); accept any
// output satisfying the stated property. Never reimplement token reading by hand.
#include "testlib.h"

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // inf  — the test input
    // ouf  — the contestant's output
    // ans  — the jury's answer
    //
    // Simple exact-value case:
    // int n = inf.readInt();
    // long long claimed = ouf.readLong();
    // long long jury    = ans.readLong();
    // if (claimed != jury) quitf(_wa, "expected %lld, got %lld", jury, claimed);
    //
    // For "print any valid X" problems, verify the property directly rather
    // than comparing to ans. Two rules that matter more than they look:
    //
    // 1. VALIDATE INDICES BEFORE USING THEM. If the property check involves
    //    reading a participant-supplied index/reference (e.g. "output a valid
    //    vertex ordering"), range-check it against the input's declared bounds
    //    BEFORE using it to index anything — a malformed submission handing
    //    you an out-of-range value can otherwise crash the CHECKER itself
    //    (undefined behavior), not just fail cleanly with _wa. Example:
    //
    //    int n = inf.readInt();
    //    int idx = ouf.readInt();
    //    if (idx < 1 || idx > n) quitf(_wa, "index %d out of range [1,%d]", idx, n);
    //    // only now is it safe to use idx to index a size-n structure
    //
    // 2. CONFIRM THE OUTPUT'S SHAPE, NOT JUST EACH VALUE'S VALIDITY. If the
    //    problem says "print exactly k lines," verify exactly k were printed
    //    — a checker that validates each value it reads without confirming
    //    the participant didn't print extra/fewer than required will silently
    //    accept malformed output shape. Example, after reading everything you
    //    expect:
    //
    //    ouf.readEof();  // fails if the participant printed anything extra

    quitf(_ok, "correct");
}
