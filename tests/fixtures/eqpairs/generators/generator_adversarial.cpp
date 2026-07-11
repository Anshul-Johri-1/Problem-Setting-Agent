// Worst case for the O(n^2) brute: max n, all equal (also maximizes the answer,
// exposing 32-bit overflow in WA3). -n <N> -seed <S>
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int n = opt<int>("n", 70000);
    (void)opt<long long>("seed", 0);   // consume; testlib folds argv into the RNG seed
    printf("1\n%d\n", n);
    for (int i = 0; i < n; ++i)
        printf("1%c", i + 1 == n ? '\n' : ' ');
    return 0;
}
