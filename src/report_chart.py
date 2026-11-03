"""QtAgg presentation of already-computed report periods; no data access."""
from datetime import datetime
import math

from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import dates as mdates
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np

from ui_components import ACCENT, METRIC_COLORS, MUTED, LINE

TITLES = {"Transactions": "Sales Transactions", "Units_Sold": "Units Sold",
          "Estimated Revenue": "Estimated Revenue"}


class ReportChart(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        figure = Figure(facecolor="white", layout="constrained")
        super().__init__(figure)
        self.setParent(parent)
        self.axes = figure.add_subplot(111)
        self.rows = []
        self.x = np.array([])
        self.mode = "empty"
        self.metric_key = "Estimated Revenue"
        self.bars = []
        self.line = self.area = None
        self._hover_index = None
        self.mpl_connect("motion_notify_event", self._hover)
        self.mpl_connect("figure_leave_event", self._leave)

    def set_periods(self, periods, grouping, metric):
        self._leave()
        self.axes.clear()
        self.rows = [] if periods is None else periods.to_dict("records")
        self.metric_key = metric
        self.bars = []
        self.line = self.area = None
        self.x = np.array([])
        self.mode = "empty"
        if not self.rows:
            self.draw_idle()
            return
        ax = self.axes
        color = METRIC_COLORS.get(metric, ACCENT)
        values = np.array([float(row[metric]) for row in self.rows])
        dates = [datetime.fromisoformat(row["Period"]) for row in self.rows]
        if len(self.rows) <= 18:
            self.mode = "bar"
            self.x = np.arange(len(values), dtype=float)
            self.bars = ax.bar(self.x, values, width=.22 if len(values) == 1 else .48,
                               color=color, edgecolor=color, zorder=3)
            labels = [d.strftime("%b %Y") if grouping == "Aylık" else
                      f"Q{(d.month - 1) // 3 + 1} {d.year}" if grouping == "Üç aylık" else
                      str(d.year) if grouping == "Yıllık" else row["Period"]
                      for d, row in zip(dates, self.rows)]
            ax.set_xticks(self.x, labels, rotation=35 if len(values) > 5 else 0,
                          ha="right" if len(values) > 5 else "center")
            ax.set_xlim(-.5, len(values) - .5)
        else:
            self.mode = "line"
            self.x = mdates.date2num(dates)
            self.line, = ax.plot(self.x, values, color=color, linewidth=2.2, zorder=3)
            self.area = ax.fill_between(self.x, 0, values, color=color, alpha=.12, zorder=2)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            ax.set_xlim(self.x[0], self.x[-1])
        maximum = max(1, float(values.max()))
        if metric == "Estimated Revenue":
            ax.set_ylim(0, maximum * 1.15)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.yaxis.set_major_formatter(FuncFormatter(
                lambda value, _: f"${value:,.2f}" if maximum < 1000 else f"${value:,.0f}"))
        else:
            top = max(1, math.ceil(maximum / 4) * 4)
            ax.set_ylim(0, top)
            ax.set_yticks(np.linspace(0, top, 5))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        ax.set_ylabel("USD · Estimated Revenue" if metric == "Estimated Revenue" else TITLES[metric],
                      color=MUTED, fontfamily="Segoe UI", fontsize=9)
        ax.set_facecolor("white")
        ax.set_axisbelow(True)
        ax.grid(axis="y", color="#EDF0F5")
        ax.tick_params(axis="both", colors=MUTED, labelsize=9, length=0)
        for side, spine in ax.spines.items():
            spine.set_visible(side in ("left", "bottom"))
            spine.set_color(LINE)
        for tick in ax.get_xticklabels() + ax.get_yticklabels():
            tick.set_fontfamily("Segoe UI")
        self.draw_idle()

    def tooltip_text(self, index):
        row = self.rows[index]
        value = row[self.metric_key]
        formatted = f"${value:,.2f}" if self.metric_key == "Estimated Revenue" else f"{int(value):,}"
        return f"{row['Period']} · {TITLES[self.metric_key]}: {formatted}"

    def _hover(self, event):
        if not self.rows or event.inaxes is not self.axes or event.xdata is None:
            self._leave()
            return
        index = int(np.argmin(np.abs(self.x - event.xdata)))
        value = float(self.rows[index][self.metric_key])
        if self.mode == "bar":
            hit = self.bars[index].contains(event)[0]
        else:
            # Match the old line/area interaction, including the filled area.
            pixel = self.axes.transData.transform((self.x[index], value))
            hit = (event.ydata is not None and 0 <= event.ydata <= value) or abs(event.y - pixel[1]) <= 8
        if hit:
            self._hover_index = index
            QToolTip.showText(QCursor.pos(), self.tooltip_text(index), self)
        else:
            self._leave()

    def _leave(self, *_):
        self._hover_index = None
        QToolTip.hideText()

    def hideEvent(self, event):
        self._leave()
        super().hideEvent(event)

