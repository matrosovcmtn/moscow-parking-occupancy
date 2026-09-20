"""Обложка датасета: недельный ритм занятости. Тепловая карта час × день недели.

Форма выбрана по задаче данных: непрерывная величина по двум циклическим осям.
Цвет — последовательный, один тон светлый→тёмный (синяя шкала 100→700),
монотонность светлоты проверена: L от 0.905 до 0.338 равным шагом.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
cmap = LinearSegmentedColormap.from_list("ofm_blue", RAMP)

piv = pd.read_csv("/tmp/kag/rhythm.csv", index_col=0)
m = piv.values
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

fig = plt.figure(figsize=(12, 6), dpi=100, facecolor=SURFACE)
ax = fig.add_axes([0.068, 0.20, 0.80, 0.545])
ax.set_facecolor(SURFACE)

# Зазор между ячейками даёт сетку цветом поверхности — она же разделитель
im = ax.imshow(m, aspect="auto", cmap=cmap, vmin=m.min(), vmax=m.max(),
               interpolation="nearest")
ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
ax.set_yticks(np.arange(-0.5, 7, 1), minor=True)
ax.grid(which="minor", color=SURFACE, linewidth=2)
ax.tick_params(which="minor", length=0)

ax.set_xticks(range(0, 24, 3))
ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)], color=INK_SOFT, fontsize=11)
ax.set_yticks(range(7))
ax.set_yticklabels(days, color=INK_SOFT, fontsize=11)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0, pad=6)
ax.set_xlabel("hour of day, Moscow time", color=INK_SOFT, fontsize=11, labelpad=9)

# Заголовок и подпись — текстовыми токенами, не цветом серии
fig.text(0.068, 0.895, "Moscow parking fills up on a weekly clock",
         color=INK, fontsize=25, fontweight="bold", va="top")
fig.text(0.068, 0.815,
         "Mean occupancy of 210 municipal lots · 4.6M half-hourly snapshots · Mar 2025 – Sep 2026",
         color=INK_SOFT, fontsize=13, va="top")

cax = fig.add_axes([0.885, 0.20, 0.018, 0.545])
cb = fig.colorbar(im, cax=cax)
cb.outline.set_visible(False)
cb.ax.tick_params(length=0, colors=INK_SOFT, labelsize=10, pad=6)
cb.set_ticks([m.min(), m.max()])
cb.set_ticklabels([f"{m.min():.0f}%", f"{m.max():.0f}%"])
cb.ax.set_title("occupied", color=INK_SOFT, fontsize=10, pad=10, loc="left")

fig.text(0.068, 0.065,
         "github.com/matrosovcmtn/moscow-parking-occupancy · CC BY 4.0",
         color=INK_SOFT, fontsize=10.5, va="center")

fig.savefig("/tmp/kag/cover.png", facecolor=SURFACE)
print("сохранено /tmp/kag/cover.png")
