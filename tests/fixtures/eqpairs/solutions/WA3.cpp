// WA3 (WA) — 32-bit overflow. Correct O(n) algorithm but accumulates into a
// 32-bit int. Fine on small tiers; on the n=70000 all-equal test the answer is
// C(70000,2)=2,449,965,000 > 2^31-1, so `ans` overflows to a negative value → WA.
// A bug that only bites at max scale — exactly why the adversarial tier exists.
#include <bits/stdc++.h>
using namespace std;
int main() {
    int t; if (scanf("%d", &t) != 1) return 0;
    while (t--) {
        int n; scanf("%d", &n);
        unordered_map<long long, long long> f;
        for (int i = 0; i < n; ++i) { long long x; scanf("%lld", &x); f[x]++; }
        int ans = 0;  // BUG: should be long long
        for (auto& kv : f) ans += (int)(kv.second * (kv.second - 1) / 2);
        printf("%d\n", ans);
    }
    return 0;
}
