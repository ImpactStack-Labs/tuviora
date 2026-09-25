"""Budget, payment and summary endpoints for event leads."""

from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BudgetItem, Payment
from .permissions import lead_event_or_deny
from .services.summary import event_summary


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


class EventSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        return Response(event_summary(event))


class EventPaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = lead_event_or_deny(event_id, request.user)
        if event.organizer_id != request.user.pk:
            raise PermissionDenied("Only the organizer can view payments.")

        payments = (
            Payment.objects.filter(registration__event=event)
            .select_related("registration__user")
            .order_by("-created_at")
        )
        return Response([
            {
                "id": p.id,
                "reference": p.reference,
                "attendee": (
                    p.registration.user.get_full_name()
                    or p.registration.user.username
                ),
                "method": p.method,
                "amount": f"{p.amount:.2f}",
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in payments
        ])
