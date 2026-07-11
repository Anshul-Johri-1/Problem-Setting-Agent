# WA2 (WA) — wrong invariant: counts how many elements are duplicated rather
# than the number of pairs (sums the frequencies of repeated values instead of
# C(v,2)). Plausible-looking but algorithmically wrong.
# EXPECTED_VERDICT: WA
import sys
from collections import Counter


def main():
    data = sys.stdin.buffer.read().split()
    idx = 0
    t = int(data[idx]); idx += 1
    out = []
    for _ in range(t):
        n = int(data[idx]); idx += 1
        c = Counter(int(data[idx + i]) for i in range(n)); idx += n
        out.append(str(sum(v for v in c.values() if v > 1)))  # BUG: not C(v,2)
    sys.stdout.write("\n".join(out) + "\n")


main()
