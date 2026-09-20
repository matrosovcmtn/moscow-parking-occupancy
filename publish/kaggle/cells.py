# --- CELL 1 ---
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BASE = "/kaggle/input/moscow-parking-occupancy"
occ = pd.read_parquet(f"{BASE}/occupancy.parquet")
spots = pd.read_parquet(f"{BASE}/parking_spots.parquet")

print(f"occupancy    : {len(occ):,} rows, {occ.time.min()} .. {occ.time.max()}")
print(f"parking_spots: {len(spots)} lots, {int(spots.total_spaces.sum()):,} spaces")
occ.head()

# --- CELL 2 ---
# The rhythm is a local-time phenomenon; timestamps are UTC.
t = occ.time.dt.tz_convert("Europe/Moscow")
occ["dow"], occ["hour"] = t.dt.dayofweek, t.dt.hour

rhythm = occ.groupby(["dow", "hour"]).occupancy_rate.mean().unstack("hour")

RAMP = ["#cde2fb","#b7d3f6","#9ec5f4","#86b6ef","#6da7ec","#5598e7","#3987e5",
        "#2a78d6","#256abf","#1c5cab","#184f95","#104281","#0d366b"]
cmap = LinearSegmentedColormap.from_list("seq_blue", RAMP)

fig, ax = plt.subplots(figsize=(12, 3.6))
im = ax.imshow(rhythm.values, aspect="auto", cmap=cmap, interpolation="nearest")
ax.set_yticks(range(7), ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
ax.set_xticks(range(0, 24, 3), [f"{h:02d}" for h in range(0, 24, 3)])
ax.set_xlabel("hour of day, Moscow time")
ax.set_title("Mean occupancy by weekday and hour", loc="left", fontsize=13)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
fig.colorbar(im, ax=ax, pad=0.01).set_label("% occupied")
plt.tight_layout(); plt.show()

# --- CELL 3 ---
# City-wide average over the last two weeks. Deliberately not a single lot:
# picking one is cherry-picking, and the extremes are degenerate anyway -
# some lots sit pinned at 100% for days, the "most variable" one just flips
# between 0 and 100. The average shows the cycle that actually generalises.
since = occ.time.max() - pd.Timedelta(days=14)
recent = occ[occ.time >= since].copy()
recent["slot"] = recent.time.dt.floor("30min").dt.tz_convert("Europe/Moscow")
city = recent.groupby("slot").occupancy_rate.mean()

fig, ax = plt.subplots(figsize=(12, 3.2))
ax.plot(city.index, city.values, color="#2a78d6", linewidth=2)
ax.fill_between(city.index, city.values, color="#2a78d6", alpha=0.12)

# Shade weekends so the weekly cycle is readable without counting days
for day, grp in city.groupby(city.index.normalize()):
    if day.dayofweek >= 5:
        ax.axvspan(day, day + pd.Timedelta(days=1), color="#0b0b0b", alpha=0.045, lw=0)

ax.set_ylim(0, 100)
ax.set_ylabel("% occupied")
ax.set_title("Average across all 210 lots, last two weeks (weekends shaded)",
             loc="left", fontsize=13)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
plt.tight_layout(); plt.show()

# --- CELL 4 ---
# How predictable is it? Two naive baselines on a 30-day holdout.
# Snap to the 30-minute grid and pivot wide — shifting a matrix is far cheaper
# than groupby().resample() over 4.6M rows.
occ["slot"] = occ.time.dt.floor("30min")
wide = occ.pivot_table(index="slot", columns="parking_id",
                       values="occupancy_rate", aggfunc="mean")
wide = wide.asfreq("30min")                      # make gaps explicit
print(f"grid: {wide.shape[0]:,} slots x {wide.shape[1]} lots")

cutoff = wide.index.max() - pd.Timedelta(days=30)
truth = wide.loc[wide.index > cutoff]

for label, periods in [("30 minutes ago", 1), ("same time last week", 336)]:
    pred = wide.shift(periods).loc[truth.index]
    mae = (truth - pred).abs().stack().mean()
    print(f"MAE, {label:22}: {mae:5.2f} percentage points")

# --- CELL 5 ---
mean_occ = occ.groupby("parking_id").occupancy_rate.mean()
geo = spots.set_index("id").join(mean_occ.rename("mean_occ")).dropna(subset=["mean_occ"])

fig, ax = plt.subplots(figsize=(7.5, 7.5))
sc = ax.scatter(geo.longitude, geo.latitude, c=geo.mean_occ, cmap=cmap,
                s=geo.total_spaces / 3 + 12, edgecolor="white", linewidth=0.6)
ax.set_title("Municipal lots: size = capacity, colour = mean occupancy",
             loc="left", fontsize=13)
ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.colorbar(sc, ax=ax, pad=0.02).set_label("% occupied")
plt.tight_layout(); plt.show()
