// Deterministic boundary/degenerate generator (§12). Flag-driven via argv.
//   gen_edge --case=min | --case=max | --case=n1 | --case=all_equal | ...
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    string kase = opt<string>("case", "min");

    // TODO: emit a deterministic edge case for `kase`. Keep these small enough
    // that the brute solution trivially passes. Example:
    // if (kase == "min")       { println(1); println(1, 1); }
    // else if (kase == "max")  { /* max constraints */ }
    // else if (kase == "n1")   { /* n == 1 */ }
    // else if (kase == "all_equal") { /* all values equal */ }

    return 0;
}
