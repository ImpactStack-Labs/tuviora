"""Private Africa's Talking conference callback.

Provider authentication must be implemented and verified before
this endpoint is allowed to process PINs or return conference XML.
"""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def conference_callback(request):
    """Reject calls until provider authentication is configured."""
    return HttpResponse(
        "Conference callback authentication is not configured.",
        status=503,
    )
