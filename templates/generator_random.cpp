// Uniform random generator, small→medium sizes (§12). argv-driven.
//   gen_random -n <N> -seed <S>
// testlib seeds its RNG from the full argv, so distinct args ⇒ distinct tests.
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int n = opt<int>("n", 1000);

    // TODO: emit one (multitest-packed if applicable) random case of size n.
    // Use rnd.next(lo, hi) for values. Example:
    // println(n);
    // for (int i = 0; i < n; ++i) cout << rnd.next(1, 1000000000) << " \n"[i+1==n];

    return 0;
}
