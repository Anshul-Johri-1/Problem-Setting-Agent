// correct.cpp (MA) — O(n) frequency count. AC everywhere.
#include <bits/stdc++.h>
using namespace std;
int main() {
    int t; if (scanf("%d", &t) != 1) return 0;
    while (t--) {
        int n; scanf("%d", &n);
        unordered_map<long long, long long> f;
        for (int i = 0; i < n; ++i) { long long x; scanf("%lld", &x); f[x]++; }
        long long ans = 0;
        for (auto& kv : f) ans += kv.second * (kv.second - 1) / 2;
        printf("%lld\n", ans);
    }
    return 0;
}
