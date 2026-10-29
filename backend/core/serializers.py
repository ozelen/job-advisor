from rest_framework import serializers

from . import models


def owned(model_cls):
    class S(serializers.ModelSerializer):
        class Meta:
            model = model_cls
            fields = "__all__"
            read_only_fields = ["owner", "created_at", "updated_at"]

    S.__name__ = f"{model_cls.__name__}Serializer"
    return S


def child(model_cls):
    class S(serializers.ModelSerializer):
        class Meta:
            model = model_cls
            fields = "__all__"

    S.__name__ = f"{model_cls.__name__}Serializer"
    return S


OpportunitySerializer = owned(models.Opportunity)
DocumentSerializer = owned(models.Document)
NoteSerializer = owned(models.Note)
GoalSerializer = owned(models.Goal)
PersonSerializer = child(models.Person)
CommunicationSerializer = child(models.Communication)
StatusChangeSerializer = child(models.StatusChange)
RoundSerializer = child(models.Round)
