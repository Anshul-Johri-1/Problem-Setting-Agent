// Deterministic edge cases. --case=min | alleq_small
#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    string kase = opt<string>("case", "min");
    if (kase == "min") {
        printf("1\n1\n1\n");                 // t=1, n=1, single element
    } else if (kase == "alleq_small") {
        printf("1\n5\n7 7 7 7 7\n");          // all equal, tiny
    } else {
        printf("1\n3\n1 2 1\n");
    }
    return 0;
}
