from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

STATUSES = ["lead", "applied", "screening", "interviewing", "offer", "accepted", "rejected", "withdrawn", "paused"]
CLOSED = {"accepted", "rejected", "withdrawn"}


class Owned(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Opportunity(Owned):
    """One role at one company. Columns mirror the vault's `00 - INPUT.md` frontmatter."""

    slug = models.CharField(max_length=200)  # vault folder name, e.g. "Technical Lead at Autodesk"
    company = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[(s, s) for s in STATUSES], default="lead")
    priority = models.CharField(max_length=20, blank=True)
    initiate = models.CharField(max_length=20, blank=True)  # application | recruiter | referral | inbound
    source = models.CharField(max_length=50, blank=True)
    url = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    remote = models.BooleanField(null=True)
    seniority = models.CharField(max_length=200, blank=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True)
    per = models.CharField(max_length=10, blank=True)  # year | month | day | hour
    cv_version = models.CharField(max_length=200, blank=True)
    applied = models.DateField(null=True, blank=True)
    next_action = models.TextField(blank=True)
    next_action_date = models.DateField(null=True, blank=True)
    outcome = models.TextField(blank=True)
    summary = models.TextField(blank=True)  # the note body under the frontmatter
    vault_path = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [("owner", "slug")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.role} at {self.company}"


class Person(models.Model):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="people")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=300, blank=True)
    channel = models.CharField(max_length=300, blank=True)
    notes = models.TextField(blank=True)


class Communication(models.Model):
    """One row of the communication log."""

    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="communications")
    at = models.CharField(max_length=50)  # as written: "2026-09-03 16:00 CET", "2026-08-26/27"
    day = models.DateField(null=True, blank=True)  # parsed when possible
    channel = models.CharField(max_length=100, blank=True)
    who = models.CharField(max_length=300, blank=True)
    direction = models.CharField(max_length=20, blank=True)  # in | out | in/out
    gist = models.TextField(blank=True)

    class Meta:
        ordering = ["-day", "-id"]


class StatusChange(models.Model):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="status_changes")
    at = models.CharField(max_length=50)
    day = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["day", "id"]


class Round(models.Model):
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="rounds")
    at = models.DateTimeField(null=True, blank=True)
    kind = models.CharField(max_length=50, blank=True)  # screen | technical | system design | final | negotiation
    outcome = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["at", "id"]


class Document(Owned):
    """A Markdown file: JD, tailored CV, cover letter, research, prep, retro; or a base CV / job posting without an opportunity."""

    KINDS = ["jd", "cv", "cl", "research", "fit", "prep", "retro", "conversation", "cv_base", "other"]
    opportunity = models.ForeignKey(Opportunity, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=20, choices=[(k, k) for k in KINDS], default="other")
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)  # frontmatter; dates become ISO strings
    path = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [("owner", "path")]
        ordering = ["path"]


class Note(Owned):
    """Strategy layer: profile, positioning, roadmap, protocol, and one row per lesson/decision. Append-only by convention."""

    KINDS = ["profile", "positioning", "roadmap", "protocol", "lesson", "decision", "retro", "checkin", "other"]
    kind = models.CharField(max_length=20, choices=[(k, k) for k in KINDS], default="other")
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    day = models.DateField(null=True, blank=True)
    path = models.CharField(max_length=500, blank=True)
    position = models.PositiveIntegerField(default=0)  # section order within path

    class Meta:
        unique_together = [("owner", "path", "position")]
        ordering = ["-day", "path", "position"]


class Goal(Owned):
    title = models.CharField(max_length=300)
    target = models.FloatField(null=True, blank=True)
    progress = models.FloatField(default=0)
    unit = models.CharField(max_length=50, blank=True)
    due = models.DateField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["done_at", "due", "id"]
