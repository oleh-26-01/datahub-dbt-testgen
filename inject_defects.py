"""Corrupt the validation seeds so the generated tests have something to catch.

A generated test suite that passes on everything is worthless. Each defect below
violates exactly one thing the catalog's documentation asserts.
"""

import csv
import pathlib
import sys

SEEDS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "validation/seeds")


def edit(table, fn):
    p = SEEDS / f"{table}_seed.csv"
    rows = list(csv.reader(p.open(encoding="utf-8")))
    head, body = rows[0], rows[1:]
    fn(head, body)
    with p.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([head] + body)


def set_cell(head, body, row, col, value):
    body[row][head.index(col)] = value


# 1. duplicate primary key — customers.customer_id is declared "Primary key."
edit("customers", lambda h, b: set_cell(h, b, 1, "customer_id", b[0][h.index("customer_id")]))

# 2. NULL in a documented key column
edit("orders", lambda h, b: set_cell(h, b, 3, "order_id", ""))

# 3. value outside the documented lifecycle (Orders Table lists six states)
edit("orders", lambda h, b: set_cell(h, b, 5, "order_status", "Refunded"))

# 4. dangling foreign key — no such order
edit("order_items", lambda h, b: set_cell(h, b, 2, "order_id", "999999"))

print("injected 4 defects into", SEEDS)
