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
    // TODO: read the contestant output with ouf.read* and validate it against
    // the input (inf) and, if useful, the jury answer (ans). Example skeleton:
    //
    // int n = inf.readInt();
    // long long claimed = ouf.readLong();
    // long long jury    = ans.readLong();
    // if (claimed != jury) quitf(_wa, "expected %lld, got %lld", jury, claimed);
    //
    // For "print any valid X" problems, verify the property directly rather
    // than comparing to ans.

    quitf(_ok, "correct");
}
