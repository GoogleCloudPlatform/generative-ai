#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa


"""Amplifies the hand-written "hero" CSVs in data/ up to demo-realistic volume.

Why this exists
---------------
A model can write 80 rows of believable, internally consistent business data. It
cannot write 20,000 - not affordably, and not without the quality collapsing into
repetition halfway down. But a demo that opens with "our order table has 63 rows"
does not read as an enterprise system, and no aggregate over 63 rows is
interesting.

So the split is: the model writes the rows the demo script actually names (the
hero rows), and this script deterministically expands the tables around them.
Hero rows are preserved verbatim and stay at the top of the file, so every id a
demo prompt refers to still resolves. Everything added after them is sampled from
what the hero rows already show, which is why the output looks like the same
business rather than like noise.

Nothing here is model-driven or random-at-runtime: same input, same seed, same
bytes out. Re-running is safe - the first run stashes the hero file as
`<table>.hero.csv` and every later run amplifies from that stash, never from
already-amplified output.

Usage
-----
    # Per-table targets from a spec (what the skill writes):
    python3 scripts/amplify_data.py --data-dir ./data --spec ./data/data_scale_spec.json

    # One target for every fact table (a table with at least one foreign key):
    python3 scripts/amplify_data.py --data-dir ./data --scale 20000

    # Explicit table list:
    python3 scripts/amplify_data.py --data-dir ./data --scale 20000 --tables orders,order_items

    # Undo: restore the hero CSVs and delete the stashes.
    python3 scripts/amplify_data.py --data-dir ./data --restore

Spec format (`data/data_scale_spec.json`) - every key optional
--------------------------------------------------------------
    {
      "seed": 1234,
      "target_rows": { "orders": 20000, "order_items": 62000 },
      "tables": {
        "orders": {
          "pk": "order_id",
          "columns": {
            "order_date": {"type": "date",        "start": "2025-04-01", "end": "2026-03-31"},
            "status":     {"type": "categorical", "values": {"completed": 0.82, "pending": 0.11, "cancelled": 0.07}},
            "amount":     {"type": "number",      "min": 1000, "max": 900000, "decimals": 0}
          }
        }
      }
    }

Only describe a column when the hero rows misrepresent it - the usual case being
dates, because 80 hand-written rows tend to sit inside one week while the demo
narrative spans a fiscal year. Every column you leave out is resampled from the
hero rows' own distribution: categories keep their observed frequencies, numbers
are drawn from the observed values with jitter and clamped to the observed range,
free text is reused verbatim, blanks keep their observed rate. Foreign keys are
detected by name (a column named like another table's primary key) and drawn from
that table's *amplified* key set, so referential integrity holds at any scale.

Two things the spec deliberately does not do. `min`/`max` are clamps on the
resampled hero values, so they can narrow a range but never stretch one - asking
for a 2,000,000 ceiling over hero rows that top out at 480,000 gets you 480,000-ish,
because inventing an order ten times larger than any the model wrote is how demo
data starts contradicting the narrative around it. And the hero rows themselves are
never rewritten to fit the spec: give a date range of FY2025 over hero rows dated
last week and those rows keep last week's dates. If a hero row is wrong, fix the
hero row.
"""

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta

HERO_SUFFIX = ".hero.csv"
DEFAULT_SEED = 1234
DEFAULT_MAX_ROWS = 200000
JITTER = 0.35

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})([ T])(\d{2}:\d{2}(:\d{2})?)$")
_BOOLS = {"true", "false", "yes", "no", "y", "n", "1", "0"}
_PK_TAIL_RE = re.compile(r"^(?P<prefix>.*?)(?P<num>\d+)(?P<suffix>\D*)$")


# --------------------------------------------------------------------------- IO


def read_csv(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError("%s is empty" % path)
    return rows[0], rows[1:]


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def discover_tables(data_dir):
    """Return {table_name: csv_path}, reading from the hero stash when present."""
    out = OrderedDict()
    for name in sorted(os.listdir(data_dir)):
        if not name.endswith(".csv") or name.endswith(HERO_SUFFIX):
            continue
        table = name[: -len(".csv")]
        stash = os.path.join(data_dir, table + HERO_SUFFIX)
        out[table] = stash if os.path.exists(stash) else os.path.join(data_dir, name)
    return out


# ------------------------------------------------------------------- inspection


def _nonempty(values):
    return [v for v in values if v is not None and v.strip() != ""]


def preferred_pk_names(table):
    """The key column names that would mean "this table's own identity"."""
    singular = table[:-1] if table.endswith("s") else table
    return [table + "_id", singular + "_id", "id", table + "_code", singular + "_code"]


def guess_pk(header, rows, table, override=None):
    """The column that identifies a row: unique, non-empty, id-shaped."""
    if override:
        return override if override in header else None
    preferred = preferred_pk_names(table)
    candidates = []
    for i, col in enumerate(header):
        vals = [r[i] if i < len(r) else "" for r in rows]
        if not vals or len(_nonempty(vals)) != len(vals):
            continue
        if len(set(vals)) != len(vals):
            continue
        low = col.lower()
        if low in preferred:
            return col
        if low.endswith("_id") or low.endswith("_code") or low == "id":
            candidates.append(col)
    return candidates[0] if candidates else None


def classify(col, values):
    """Infer how a column should be regenerated from what the hero rows show."""
    vals = _nonempty(values)
    if not vals:
        return "blank"
    distinct = len(set(vals))
    if all(_DATETIME_RE.match(v) for v in vals):
        return "datetime"
    if all(_DATE_RE.match(v) for v in vals):
        return "date"
    if all(v.lower() in _BOOLS for v in vals) and distinct <= 2:
        return "categorical"
    if all(_INT_RE.match(v) for v in vals):
        # A small-range integer is an enum (quantity 1-5, rating 1-5, flag 0/1),
        # not a magnitude. Jittering it produces values the demo never shows.
        ints = [int(v) for v in vals]
        if distinct <= 12 and max(ints) - min(ints) <= 30:
            return "categorical"
        return "int"
    if all(_INT_RE.match(v) or _FLOAT_RE.match(v) for v in vals):
        return "float"
    if distinct <= max(12, len(vals) // 5):
        return "categorical"
    return "text"


def resolve_pk_owners(pks):
    """One column name, one owning table.

    An event log keyed only by `order_id` looks exactly like a table whose
    primary key is `order_id`, because in its own 25 hero rows that column is
    unique. Left alone, the log claims ownership of the key, `orders` is then
    read as the *child*, the dependency order inverts, and the log is skipped as
    master data. So when two tables claim one key, it belongs to the one named
    after it; for everyone else the column is a foreign key, which is what it is.
    """
    claims = {}
    for table, pk in pks.items():
        if pk:
            claims.setdefault(pk, []).append(table)
    for col, owners in claims.items():
        if len(owners) < 2:
            continue
        named = sorted(t for t in owners if col.lower() in preferred_pk_names(t.lower()))
        winner = named[0] if named else sorted(owners)[0]
        for table in owners:
            if table != winner:
                pks[table] = None
    return pks


class ColumnModel(object):
    """Everything needed to draw one more value for one column."""

    def __init__(self, name, values, kind, spec=None):
        self.name = name
        self.kind = kind
        self.spec = spec or {}
        self.values = values
        present = _nonempty(values)
        self.blank_rate = 0.0 if not values else 1.0 - (len(present) / float(len(values)))
        self.pool = present or [""]
        self.freq = Counter(present)
        if kind in ("int", "float"):
            nums = [float(v) for v in present]
            self.lo = self.spec.get("min", min(nums) if nums else 0)
            self.hi = self.spec.get("max", max(nums) if nums else 0)
            if "decimals" in self.spec:
                self.decimals = int(self.spec["decimals"])
            elif kind == "int":
                self.decimals = 0
            else:
                self.decimals = max(len(v.split(".")[1]) for v in present if "." in v) if any("." in v for v in present) else 2
        if kind in ("date", "datetime"):
            self.fmt_sep, self.fmt_time = self._date_shape(present)
            self.start = self._parse_day(self.spec.get("start")) or min(self._days(present))
            self.end = self._parse_day(self.spec.get("end")) or max(self._days(present))
            if self.end < self.start:
                self.start, self.end = self.end, self.start
        if kind == "categorical" and isinstance(self.spec.get("values"), dict):
            self.freq = Counter()
            for k, w in self.spec["values"].items():
                self.freq[str(k)] = max(0.0, float(w))
            if not sum(self.freq.values()):
                self.freq = Counter(present)

    @staticmethod
    def _date_shape(present):
        m = _DATETIME_RE.match(present[0]) if present else None
        if not m:
            return None, None
        return m.group(2), m.group(3)

    @staticmethod
    def _days(present):
        out = []
        for v in present:
            out.append(datetime.strptime(v[:10], "%Y-%m-%d").date())
        return out or [date.today()]

    @staticmethod
    def _parse_day(v):
        if not v:
            return None
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def draw(self, rnd):
        if self.blank_rate and rnd.random() < self.blank_rate:
            return ""
        if self.kind == "blank":
            return ""
        if self.kind in ("categorical", "text"):
            return self._weighted(rnd) if self.kind == "categorical" else rnd.choice(self.pool)
        if self.kind in ("int", "float"):
            base = float(rnd.choice(self.pool))
            val = base * (1.0 + rnd.uniform(-JITTER, JITTER))
            val = min(max(val, self.lo), self.hi)
            if self.decimals <= 0:
                return str(int(round(val)))
            return ("%." + str(self.decimals) + "f") % val
        if self.kind in ("date", "datetime"):
            span = (self.end - self.start).days
            day = self.start + timedelta(days=rnd.randint(0, span if span > 0 else 0))
            if self.kind == "date":
                return day.isoformat()
            hh = rnd.randint(8, 19)
            mm = rnd.choice((0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55))
            tail = "%02d:%02d" % (hh, mm)
            if self.fmt_time and self.fmt_time.count(":") == 2:
                tail += ":%02d" % rnd.randint(0, 59)
            return day.isoformat() + (self.fmt_sep or " ") + tail
        return rnd.choice(self.pool)

    def _weighted(self, rnd):
        items = list(self.freq.items())
        total = sum(w for _, w in items)
        if total <= 0:
            return rnd.choice(self.pool)
        pick = rnd.uniform(0, total)
        upto = 0.0
        for v, w in items:
            upto += w
            if pick <= upto:
                return v
        return items[-1][0]


# ----------------------------------------------------------------- key minting


class KeyMinter(object):
    """Continues a primary key series past the hero rows, in the same shape."""

    def __init__(self, table, existing):
        self.fallback = 0
        self.prefix = table.upper()[:6] + "-"
        self.suffix = ""
        self.width = 6
        self.next_num = len(existing) + 1
        self.taken = set(existing)
        shapes = [_PK_TAIL_RE.match(v) for v in existing]
        shapes = [m for m in shapes if m]
        if shapes and len(set(m.group("prefix") for m in shapes)) == 1:
            self.prefix = shapes[0].group("prefix")
            self.suffix = shapes[0].group("suffix")
            self.width = max(len(m.group("num")) for m in shapes)
            self.next_num = max(int(m.group("num")) for m in shapes) + 1

    def mint(self):
        while True:
            num = str(self.next_num)
            self.next_num += 1
            key = self.prefix + num.zfill(self.width) + self.suffix
            if key not in self.taken:
                self.taken.add(key)
                return key


# ------------------------------------------------------------------- amplifying


def order_tables(tables, pks):
    """Parents before children, so a child can draw from the parent's final keys."""
    pk_owner = {pk: t for t, pk in pks.items() if pk}
    deps = {}
    for t, (header, _rows) in tables.items():
        deps[t] = set(
            pk_owner[c] for c in header if c in pk_owner and pk_owner[c] != t
        )
    ordered, seen = [], set()

    def visit(t, stack):
        if t in seen or t in stack:
            return
        stack.add(t)
        for d in sorted(deps.get(t, ())):
            visit(d, stack)
        stack.discard(t)
        seen.add(t)
        ordered.append(t)

    for t in tables:
        visit(t, set())
    return ordered


def amplify_table(table, header, hero, target, pk, fk_pools, spec, seed):
    rnd = random.Random("%s::%d" % (table, seed))
    col_spec = (spec.get("columns") or {}) if spec else {}
    cols = []
    for i, name in enumerate(header):
        values = [r[i] if i < len(r) else "" for r in hero]
        s = col_spec.get(name) or {}
        kind = s.get("type") or classify(name, values)
        if kind == "number":
            kind = "float" if any("." in v for v in _nonempty(values)) else "int"
        cols.append(ColumnModel(name, values, kind, s))

    pk_idx = header.index(pk) if pk in header else None
    minter = KeyMinter(table, [r[pk_idx] for r in hero]) if pk_idx is not None else None
    fk_idx = {
        i: fk_pools[name]
        for i, name in enumerate(header)
        if name in fk_pools and i != pk_idx and fk_pools[name]
    }

    rows = [list(r) for r in hero]
    while len(rows) < target:
        row = []
        for i, model in enumerate(cols):
            if i == pk_idx:
                row.append(minter.mint())
            elif i in fk_idx:
                row.append(rnd.choice(fk_idx[i]))
            else:
                row.append(model.draw(rnd))
        rows.append(row)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", default="./data")
    ap.add_argument("--spec", default=None, help="path to data_scale_spec.json")
    ap.add_argument("--scale", type=int, default=0, help="target row count per selected table")
    ap.add_argument("--tables", default="", help="comma-separated table names for --scale")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    ap.add_argument("--restore", action="store_true", help="undo: put the hero CSVs back")
    args = ap.parse_args(argv)

    data_dir = args.data_dir
    if not os.path.isdir(data_dir):
        print("ERROR - no such directory: %s" % data_dir, file=sys.stderr)
        return 1

    if args.restore:
        n = 0
        for name in sorted(os.listdir(data_dir)):
            if not name.endswith(HERO_SUFFIX):
                continue
            table = name[: -len(HERO_SUFFIX)]
            os.replace(os.path.join(data_dir, name), os.path.join(data_dir, table + ".csv"))
            print("   restored %s.csv" % table)
            n += 1
        print("OK - %d table(s) restored to their hero rows." % n)
        return 0

    spec = {}
    if args.spec and os.path.exists(args.spec):
        with open(args.spec, "r", encoding="utf-8") as f:
            spec = json.load(f) or {}
    seed = args.seed if args.seed is not None else int(spec.get("seed", DEFAULT_SEED))
    targets = dict(spec.get("target_rows") or {})

    sources = discover_tables(data_dir)
    if not sources:
        print("ERROR - no CSV files in %s" % data_dir, file=sys.stderr)
        return 1

    tables = OrderedDict()
    for table, path in sources.items():
        tables[table] = read_csv(path)

    pks = resolve_pk_owners(
        {t: guess_pk(h, r, t, ((spec.get("tables") or {}).get(t) or {}).get("pk"))
         for t, (h, r) in tables.items()}
    )
    pk_owner = {pk: t for t, pk in pks.items() if pk}

    # --scale needs a table list. Absent one, pick the fact tables (those that
    # reference another table) and say so - amplifying a 40-row customer master
    # to 20,000 contradicts the narrative the model just wrote.
    if args.scale > 0:
        named = [t.strip() for t in args.tables.split(",") if t.strip()]
        if named:
            chosen = [t for t in named if t in tables]
            for t in named:
                if t not in tables:
                    print("   WARNING - --tables names '%s', which has no CSV; ignored." % t)
        else:
            chosen = [t for t, (h, _r) in tables.items()
                      if any(c in pk_owner and pk_owner[c] != t for c in h)]
            skipped = [t for t in tables if t not in chosen]
            if skipped:
                print("   Left at hero size (no foreign key, so read as master data): %s"
                      % ", ".join(skipped))
        for t in chosen:
            targets.setdefault(t, args.scale)

    if not targets:
        print("Nothing to amplify: no --scale and no target_rows in the spec.")
        return 0

    over = {t: n for t, n in targets.items() if n > args.max_rows}
    if over:
        for t, n in sorted(over.items()):
            print("ERROR - %s: %d rows exceeds --max-rows %d." % (t, n, args.max_rows),
                  file=sys.stderr)
        return 1

    fk_pools = {}
    report = []
    for table in order_tables(tables, pks):
        header, hero = tables[table]
        pk = pks.get(table)
        target = int(targets.get(table, len(hero)))
        if target <= len(hero):
            if pk and pk in header:
                fk_pools[pk] = [r[header.index(pk)] for r in hero]
            continue

        rows = amplify_table(
            table, header, hero, target, pk, fk_pools,
            (spec.get("tables") or {}).get(table) or {}, seed,
        )
        if pk and pk in header:
            fk_pools[pk] = [r[header.index(pk)] for r in rows]

        live = os.path.join(data_dir, table + ".csv")
        stash = os.path.join(data_dir, table + HERO_SUFFIX)
        if not os.path.exists(stash):
            write_csv(stash, header, hero)
        write_csv(live, header, rows)
        report.append((table, len(hero), len(rows), pk or "-"))

    if not report:
        print("Nothing to amplify: every target is at or below the current row count.")
        return 0

    width = max(len(t) for t, _, _, _ in report)
    print("Amplified (hero rows preserved verbatim at the top of each file):")
    for table, hero_n, total, pk in report:
        print("   %-*s  %6d -> %7d rows   pk=%s" % (width, table, hero_n, total, pk))
    print("OK - re-run scripts/validate_csv.py before loading into BigQuery.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
