from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase

from . import models
from .vault import import_vault, split_frontmatter, tables, to_date

HUB = """---
company: Acme
role: Lead
status: interviewing    # lead | applied | ...
remote: true
salary_min: 450
currency: EUR
per: day
applied: 2026-08-26
next_action: Ask the rate
next_action_date: 2026-09-04
tags: [opportunity]
---

# Lead at Acme

> why it matters

## People

| Name | Role | Channel | Notes |
|------|------|---------|-------|
| Alex | Recruiter | email | owns the process |

## Communication log

| Date | Channel | Who | Direction | Gist / next step |
|------|---------|-----|-----------|------------------|
| 2026-09-03 16:00 CET | Zoom | Engineers | — | Round 2 happened |
| 2026-08-26/27 | LinkedIn | Recruiter | in/out | Inbound |

## Status history

| Date | → Status | Note |
|------|----------|------|
| 2026-08-26 | lead | Inbound |
| 2026-08-31 | interviewing | Round 1 booked |
"""

LESSONS = """---
updated: 2026-10-17
---
# Lessons

## 2026-10-17 — Tailoring fails afterwards

Body one.

## 2026-06 — The key pattern

Body two.

## Decisions log

- stop IC loops
"""


class VaultImportTest(TestCase):
    def test_import_twice_is_stable(self):
        user = get_user_model().objects.create_user("u")
        with TemporaryDirectory() as d:
            root = Path(d)
            opp = root / "opportuntities" / "Lead at Acme"
            opp.mkdir(parents=True)
            (opp / "00 - INPUT.md").write_text(HUB)
            (opp / "02 - CV.md").write_text("---\nbase_cv: 2026-05-01 - EL\nsent: 2026-06-01\n---\n# CV body")
            (root / "opportuntities" / "(TEMPLATE) ROLE at COMPANY").mkdir()
            (root / "opportuntities" / "(TEMPLATE) ROLE at COMPANY" / "00 - INPUT.md").write_text(HUB)
            (root / "cv").mkdir()
            (root / "cv" / "2026-05-01 - EL.md").write_text("# base")
            (root / "strategy").mkdir()
            (root / "strategy" / "Lessons.md").write_text(LESSONS)
            (root / "strategy" / "Profile.md").write_text("---\nupdated: 2026-06-17\n---\n# me")

            for _ in range(2):
                counts = import_vault(user, root)

        self.assertEqual(counts, {"opportunities": 1, "documents": 2, "notes": 4})
        o = models.Opportunity.objects.get()
        self.assertEqual((o.status, o.remote, float(o.salary_min), str(o.applied)), ("interviewing", True, 450.0, "2026-08-26"))
        self.assertEqual(o.people.count(), 1)
        self.assertEqual([str(c.day) for c in o.communications.all()], ["2026-09-03", "2026-08-26"])
        self.assertEqual(list(o.status_changes.values_list("status", flat=True)), ["lead", "interviewing"])
        cv = o.documents.get(kind="cv")
        self.assertEqual((cv.meta["base_cv"], cv.meta["sent"]), ("2026-05-01 - EL", "2026-06-01"))
        self.assertEqual(models.Document.objects.filter(kind="cv_base").count(), 1)
        self.assertEqual(set(models.Note.objects.values_list("kind", flat=True)), {"profile", "lesson", "decision"})
        self.assertEqual(str(models.Note.objects.get(position=0, kind="lesson").day), "2026-10-17")

    def test_frontmatter_falls_back_when_not_yaml(self):
        meta, body = split_frontmatter("---\nstatus: lead   # lead | applied\ncv_version: tailored — see [[02 - CV]] (base: 2026-05-01 - EL)\napplied: 2026-08-26\n---\nbody")
        self.assertEqual((meta["status"], meta["cv_version"], str(to_date(meta["applied"])), body), ("lead", "tailored — see [[02 - CV]] (base: 2026-05-01 - EL)", "2026-08-26", "body"))

    def test_tables_skip_separator_and_blank_rows(self):
        t = tables("## X\n\n| A | B |\n|---|---|\n|  |  |\n| 1 | 2 |\n")
        self.assertEqual(t, {"X": [{"a": "1", "b": "2"}]})
