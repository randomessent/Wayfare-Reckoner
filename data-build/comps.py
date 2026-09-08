"""Which cells you can actually walk between.

Islands are the whole point: without this, proving that there is no way from
Madrid to London means searching every road in western Europe before giving up.
With it the answer is two lookups.
"""
import numpy as np
from collections import deque

m = np.load("landmask_0p1.npy")
H, W = m.shape
comp = np.zeros((H, W), dtype=np.int32)
sizes = [0]
cid = 0
for j in range(H):
    row = m[j]
    for i in range(W):
        if not row[i] or comp[j, i]:
            continue
        cid += 1
        n = 0
        q = deque([(i, j)])
        comp[j, i] = cid
        while q:
            ci, cj = q.popleft()
            n += 1
            for dj in (-1, 0, 1):
                nj = cj + dj
                if nj < 0 or nj >= H:
                    continue
                for di in (-1, 0, 1):
                    ni = (ci + di) % W
                    if m[nj, ni] and not comp[nj, ni]:
                        comp[nj, ni] = cid
                        q.append((ni, nj))
        sizes.append(n)

order = sorted(range(1, cid+1), key=lambda k: -sizes[k])
remap = np.zeros(cid+1, dtype=np.uint8)
for rank, k in enumerate(order):
    remap[k] = (rank + 1) if rank < 254 else 255
out = remap[comp]
np.save("comps_0p1.npy", out)
print(f"{cid:,} components; largest {sizes[order[0]]:,} cells "
      f"({100*sizes[order[0]]/m.sum():.1f}% of land)")
for k in order[:8]:
    print(f"  {sizes[k]:>8,} cells")
def at(la, lo): return int(out[int((90-la)/0.1), int((lo+180)/0.1) % W])
for n,(la,lo) in {"Madrid":(40.4,-3.7),"London":(51.5,-0.13),"Beijing":(39.9,116.4),
                  "New York":(40.7,-74.0),"Tokyo":(35.7,139.7),"Sydney":(-33.9,151.2),
                  "Dublin":(53.3,-6.3),"Reykjavik":(64.1,-21.9)}.items():
    print(f"  {n:10s} component {at(la,lo)}")
