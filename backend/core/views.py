from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models, serializers


class OwnedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ChildViewSet(viewsets.ModelViewSet):
    filterset_fields = ["opportunity"]

    def get_queryset(self):
        return self.queryset.filter(opportunity__owner=self.request.user)


class OpportunityViewSet(OwnedViewSet):
    queryset = models.Opportunity.objects.all()
    serializer_class = serializers.OpportunitySerializer
    filterset_fields = ["status", "priority", "source", "initiate", "company"]
    search_fields = ["company", "role", "summary", "next_action"]


class DocumentViewSet(OwnedViewSet):
    queryset = models.Document.objects.all()
    serializer_class = serializers.DocumentSerializer
    filterset_fields = ["kind", "opportunity"]
    search_fields = ["title", "body"]


class NoteViewSet(OwnedViewSet):
    queryset = models.Note.objects.all()
    serializer_class = serializers.NoteSerializer
    filterset_fields = ["kind"]
    search_fields = ["title", "body"]


class GoalViewSet(OwnedViewSet):
    queryset = models.Goal.objects.all()
    serializer_class = serializers.GoalSerializer


class PersonViewSet(ChildViewSet):
    queryset = models.Person.objects.all()
    serializer_class = serializers.PersonSerializer


class CommunicationViewSet(ChildViewSet):
    queryset = models.Communication.objects.all()
    serializer_class = serializers.CommunicationSerializer


class StatusChangeViewSet(ChildViewSet):
    queryset = models.StatusChange.objects.all()
    serializer_class = serializers.StatusChangeSerializer


class RoundViewSet(ChildViewSet):
    queryset = models.Round.objects.all()
    serializer_class = serializers.RoundSerializer


class SummaryView(APIView):
    """The one shape every zelen.uk backend serves for the app's Home dashboard (fr-dashboard-summary)."""

    def get(self, request):
        today = timezone.localdate()
        goals = models.Goal.objects.filter(owner=request.user, done_at__isnull=True)
        due = models.Opportunity.objects.filter(owner=request.user, next_action_date__lte=today).exclude(status__in=models.CLOSED)
        won = models.Opportunity.objects.filter(owner=request.user, status="accepted")
        return Response(
            {
                "domain": "career",
                "asOf": timezone.now().isoformat(),
                "goals": [{"id": g.id, "title": g.title, "progress": (g.progress / g.target) if g.target else g.progress, "due": g.due} for g in goals],
                "achievements": [{"id": o.id, "title": f"Accepted: {o}", "at": o.updated_at.date()} for o in won],
                "today": [{"id": o.id, "title": f"{o}: {o.next_action}", "done": False} for o in due],
            }
        )
