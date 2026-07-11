# WA1 (WA) — off-by-one in the pair-count formula: uses v*(v+1)//2 instead of
# v*(v-1)//2, so it overcounts by v per distinct value. Wrong on essentially
# every test (including n=1: reports 1 instead of 0).
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
        out.append(str(sum(v * (v + 1) // 2 for v in c.values())))  # BUG: +1
    sys.stdout.write("\n".join(out) + "\n")


main()
