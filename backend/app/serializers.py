import json


def deserialize_generate_request(body):
    return json.loads(body)


def serialize_generate_response(care_plan):
    return {"status": "pending", "careplan_id": care_plan.id}


def serialize_status_response(care_plan):
    response = {"status": care_plan.status}
    if care_plan.status == "completed":
        response["content"] = care_plan.content
    return response


def serialize_careplan_response(patient, order, care_plan):
    return {
        "patient": f"{patient.first_name} {patient.last_name}",
        "medication": order.medication,
        "care_plan": care_plan.content,
        "status": care_plan.status,
    }
