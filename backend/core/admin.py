from django.contrib import admin

from . import models


class Inline(admin.TabularInline):
    extra = 0


class PersonInline(Inline):
    model = models.Person


class CommunicationInline(Inline):
    model = models.Communication


class StatusChangeInline(Inline):
    model = models.StatusChange


class RoundInline(Inline):
    model = models.Round


@admin.register(models.Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ["role", "company", "status", "priority", "next_action_date", "applied"]
    list_filter = ["status", "priority", "source"]
    search_fields = ["company", "role"]
    inlines = [StatusChangeInline, CommunicationInline, PersonInline, RoundInline]


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "opportunity", "path"]
    list_filter = ["kind"]


@admin.register(models.Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "day", "path"]
    list_filter = ["kind"]


admin.site.register(models.Goal)
