// Worst-case/adversarial generator at max constraints (§12). argv-driven.
//   gen_adversarial -n <MAX> -pattern=<p> -seed <S>
// Target brute's specific inefficiency so it reliably exceeds the time cap.
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int n = opt<int>("n", 100000);
    string pattern = opt<string>("pattern", "dup");

    // TODO: emit a max-size case whose structure forces brute's worst case.
    // Pick `pattern` to match the intended blow-up (e.g. many duplicates, sorted
    // input, deep recursion, hash collisions). Example:
    // if (pattern == "dup") { /* all equal → brute's O(n^2) path */ }

    return 0;
}
