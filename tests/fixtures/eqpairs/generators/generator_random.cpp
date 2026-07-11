// Uniform random with forced collisions. -n <N> -seed <S>
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int n = opt<int>("n", 1000);
    (void)opt<long long>("seed", 0);   // consume; testlib folds argv into the RNG seed
    int hi = max(1, n / 3);   // small value range => many equal pairs
    printf("1\n%d\n", n);
    for (int i = 0; i < n; ++i)
        printf("%d%c", rnd.next(1, hi), i + 1 == n ? '\n' : ' ');
    return 0;
}
