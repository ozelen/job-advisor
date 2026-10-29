"""Read the Obsidian `career/` tree into the database. Reads the vault, never writes it. Safe to run again."""

import re
from datetime import date
from pathlib import Path

import yaml

from . import models

DOC_KINDS = {"01": "jd", "02": "cv", "03": "cl", "04": "research", "05": "fit", "06": "prep", "07": "retro", "08": "conversation"}
NOTE_KINDS = {"Profile": "profile", "Positioning": "positioning", "Roadmap": "roadmap", "Advisor Protocol": "protocol"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:  # hand-written frontmatter with unquoted colons: fall back to key: value lines
        meta = {}
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(":")
            if sep and re.fullmatch(r"\w+", k.strip()):
                meta[k.strip()] = re.sub(r"\s+#.*$", "", v).strip().strip("'\"")
    return (meta if isinstance(meta, dict) else {}), text[m.end():]


def to_date(v):
    if isinstance(v, date):
        return v
    m = DATE.search(str(v or ""))
    return date.fromisoformat(m.group()) if m else None


def to_num(v):
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def to_bool(v):
    return v if isinstance(v, bool) else ({"true": True, "false": False}.get(str(v).strip().lower()))


def text(v):
    return "" if v is None else str(v).strip()


def tables(body):
    """`## Heading` -> list of row dicts keyed by lowercased header cell."""
    out, heading, header = {}, None, None
    for line in body.splitlines():
        if line.startswith("## "):
            heading, header = line[3:].strip(), None
        elif heading and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = [c.lower() for c in cells]
            elif not all(re.fullmatch(r":?-+:?", c) for c in cells) and any(cells):
                out.setdefault(heading, []).append(dict(zip(header, cells)))
    return out


def col(row, *names):
    for n in names:
        for k, v in row.items():
            if n in k:
                return v
    return ""


def import_opportunity(owner, folder: Path, root: Path):
    hub = folder / "00 - INPUT.md"
    if not hub.is_file():
        return None
    meta, body = split_frontmatter(hub.read_text())
    status = text(meta.get("status")) or "lead"
    opp, _ = models.Opportunity.objects.update_or_create(
        owner=owner,
        slug=folder.name,
        defaults=dict(
            company=text(meta.get("company")) or folder.name.split(" at ")[-1],
            role=text(meta.get("role")) or folder.name.split(" at ")[0],
            status=status if status in models.STATUSES else "lead",
            priority=text(meta.get("priority")),
            initiate=text(meta.get("initiate")),
            source=text(meta.get("source")),
            url=text(meta.get("url"))[:200],
            location=text(meta.get("location")),
            remote=to_bool(meta.get("remote")),
            seniority=text(meta.get("seniority")),
            salary_min=to_num(meta.get("salary_min")),
            salary_max=to_num(meta.get("salary_max")),
            currency=text(meta.get("currency")),
            per=text(meta.get("per")),
            cv_version=text(meta.get("cv_version")),
            applied=to_date(meta.get("applied")),
            next_action=text(meta.get("next_action")),
            next_action_date=to_date(meta.get("next_action_date")),
            outcome=text(meta.get("outcome")),
            summary=body.strip(),
            vault_path=str(hub.relative_to(root)),
        ),
    )
    t = tables(body)
    opp.people.all().delete()
    opp.communications.all().delete()
    opp.status_changes.all().delete()
    models.Person.objects.bulk_create(
        models.Person(opportunity=opp, name=col(r, "name"), role=col(r, "role"), channel=col(r, "channel"), notes=col(r, "note"))
        for r in t.get("People", []) if col(r, "name")
    )
    models.Communication.objects.bulk_create(
        models.Communication(opportunity=opp, at=col(r, "date")[:50], day=to_date(col(r, "date")), channel=col(r, "channel"), who=col(r, "who"), direction=col(r, "direction"), gist=col(r, "gist"))
        for r in t.get("Communication log", []) if col(r, "date")
    )
    models.StatusChange.objects.bulk_create(
        models.StatusChange(opportunity=opp, at=col(r, "date")[:50], day=to_date(col(r, "date")), status=col(r, "status"), note=col(r, "note"))
        for r in t.get("Status history", []) if col(r, "date")
    )
    for f in sorted(folder.glob("*.md")):
        if f.name == hub.name:
            continue
        import_document(owner, f, root, DOC_KINDS.get(f.name[:2], "other"), opp)
    return opp


def import_document(owner, f: Path, root: Path, kind, opp=None):
    meta, body = split_frontmatter(f.read_text())
    models.Document.objects.update_or_create(
        owner=owner,
        path=str(f.relative_to(root)),
        defaults=dict(opportunity=opp, kind=kind, title=f.stem, body=body.strip(), meta=meta),
    )


def import_notes(owner, f: Path, root: Path):
    meta, body = split_frontmatter(f.read_text())
    path = str(f.relative_to(root))
    kind = NOTE_KINDS.get(f.stem)
    if kind:
        models.Note.objects.update_or_create(owner=owner, path=path, position=0, defaults=dict(kind=kind, title=f.stem, body=body.strip(), day=to_date(meta.get("updated"))))
        return 1
    # Lessons.md: one note per `## ` section, the Decisions log section counts as decisions
    sections = re.split(r"^## ", body, flags=re.M)[1:]
    models.Note.objects.filter(owner=owner, path=path, position__gte=len(sections)).delete()
    for i, s in enumerate(sections):
        title, _, rest = s.partition("\n")
        kind = "decision" if title.lower().startswith("decisions") else "lesson"
        models.Note.objects.update_or_create(owner=owner, path=path, position=i, defaults=dict(kind=kind, title=title.strip()[:300], body=rest.strip(), day=to_date(title)))
    return len(sections)


def import_vault(owner, root: Path):
    root = Path(root)
    counts = {"opportunities": 0, "documents": 0, "notes": 0}
    for folder in sorted((root / "opportuntities").iterdir()) if (root / "opportuntities").is_dir() else []:
        if folder.is_dir() and not folder.name.startswith("(TEMPLATE)") and import_opportunity(owner, folder, root):
            counts["opportunities"] += 1
    for f in sorted((root / "cv").glob("*.md")) if (root / "cv").is_dir() else []:
        import_document(owner, f, root, "cv_base")
        counts["documents"] += 1
    for f in sorted((root / "jobs").glob("*.md")) if (root / "jobs").is_dir() else []:
        import_document(owner, f, root, "jd")
        counts["documents"] += 1
    for f in sorted((root / "strategy").glob("*.md")) if (root / "strategy").is_dir() else []:
        counts["notes"] += import_notes(owner, f, root)
    counts["documents"] += models.Document.objects.filter(owner=owner, opportunity__isnull=False).count()
    return counts
