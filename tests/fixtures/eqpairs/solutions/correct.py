# correct.py (OK) — same O(n) algorithm, cross-validates correct.cpp.
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
        out.append(str(sum(v * (v - 1) // 2 for v in c.values())))
    sys.stdout.write("\n".join(out) + "\n")


main()
