// WA4 (RE) — out-of-bounds access. O(n) (fast) so the runtime error is the
// verdict on EVERY test, including the max tier — a slow bug would TL first and
// violate the RE tag on Polygon (tags are strictly enforced at package build).
#include <bits/stdc++.h>
using namespace std;
int main() {
    int t; if (scanf("%d", &t) != 1) return 0;
    while (t--) {
        int n; scanf("%d", &n);
        vector<long long> a(n);
        for (auto& x : a) scanf("%lld", &x);
        long long ans = 0;
        for (auto& x : a) ans += x;   // O(n), trivial
        ans += a.at(n);               // BUG: index n is out of bounds → throws → RE
        printf("%lld\n", ans);
    }
    return 0;
}
