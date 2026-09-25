"""Budget, payment and summary endpoints for event leads."""

from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from .models import BudgetItem
from .permissions import lead_event_or_deny


class BudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = [
            "id",
            "category",
            "description",
            "vendor",
            "planned_amount",
            "actual_amount",
            "paid",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class BudgetItemListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        return lead_event_or_deny(self.kwargs["event_id"], self.request.user)

    def get_queryset(self):
        return self.get_event().budget_items.all()

    def perform_create(self, serializer):
        serializer.save(event=self.get_event(), created_by=self.request.user)


class BudgetItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        event = lead_event_or_deny(self.kwargs["event_id"], self.request.user)
        return event.budget_items.all()
