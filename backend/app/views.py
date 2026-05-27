from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from app.models import CarePlan
from app import serializers, services


@csrf_exempt
@require_POST
def generate_careplan(request):
    data = serializers.deserialize_generate_request(request.body)
    care_plan = services.create_careplan(data)
    return JsonResponse(serializers.serialize_generate_response(care_plan))


@require_GET
def get_careplan_status(request, careplan_id):
    try:
        care_plan = services.get_careplan_status(careplan_id)
    except CarePlan.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)
    return JsonResponse(serializers.serialize_status_response(care_plan))


@require_GET
def get_careplan(request, mrn):
    patient, order, care_plan = services.get_careplan_by_mrn(mrn)
    return JsonResponse(serializers.serialize_careplan_response(patient, order, care_plan))
