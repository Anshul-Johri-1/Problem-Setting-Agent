// brute.cpp (TL) — correct but O(n^2). AC on small/medium tiers, TL on the max
// (n=70000) tier only. Uses long long so it is CORRECT, just slow.
#include <bits/stdc++.h>
using namespace std;
int main() {
    int t; if (scanf("%d", &t) != 1) return 0;
    while (t--) {
        int n; scanf("%d", &n);
        vector<long long> a(n);
        for (auto& x : a) scanf("%lld", &x);
        long long ans = 0;
        for (int i = 0; i < n; ++i)
            for (int j = i + 1; j < n; ++j)
                if (a[i] == a[j]) ++ans;
        printf("%lld\n", ans);
    }
    return 0;
}
