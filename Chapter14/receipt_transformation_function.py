import functions_framework
import json
from datetime import datetime

# Helper to safely extract entities
# @functions_framework.http
def get_entity_value(entities, entity_type):
    for entity in entities:
        if entity.get('type') == entity_type:
            return entity.get('mentionText', None) # Or 'normalizedValue' if available and preferred
    return None

@functions_framework.http
def transform_receipt_data(request):
    request_json = request.get_json(silent=True)
    if not request_json or 'document_ai_output' not in request_json:
        return {"isValid": False, "errors": "Missing document_ai_output", "data_for_bq": {}}, 400
    
    # More robust check for request_json and the required key
    if not isinstance(request_json, dict) or 'document_ai_output' not in request_json:
        print(f"Error: Invalid request payload. Received raw data: {request.data}") # Log raw data for debugging
        return {"isValid": False, "errors": "Missing or invalid document_ai_output in request", "data_for_bq": {}}, 400


    doc_ai_output = request_json.get('document_ai_output')

    # Check if doc_ai_output is None or not a dictionary
    if not isinstance(doc_ai_output, dict):
        print(f"Error: document_ai_output is not a valid dictionary. Received: {doc_ai_output}")
        return {"isValid": False, "errors": "document_ai_output is not a valid dictionary", "data_for_bq": {}}, 400


    entities = doc_ai_output.get('entities', [])

    data_for_bq = {
        "doc_ai_full_text": doc_ai_output.get('text', None),
        "vendor_name": get_entity_value(entities, 'supplier_name'), # Adjust entity types based on your processor
        "total_amount": None,
        "invoice_date": None,
    }

    # Example: Extracting total amount (can be complex)
    total_amount_str = get_entity_value(entities, 'total_amount')
    if total_amount_str:
        try:
            # Clean up common currency symbols or formatting if necessary
            cleaned_amount_str = total_amount_str.replace('$', '').replace(',', '')
            data_for_bq["total_amount"] = float(cleaned_amount_str)
        except ValueError:
            pass # Could add to errors if strict parsing is needed

    # Example: Extracting invoice date
    invoice_date_str = get_entity_value(entities, 'receipt_date') 
    if invoice_date_str:
        try:
            # Document AI often provides date in 'YYYY-MM-DD' or with 'normalizedValue'
            # For simplicity, assuming it's parsable or already YYYY-MM-DD
            # If Document AI gives a full datetime object in normalizedValue:
            # date_obj = datetime.strptime(invoice_date_str, '%Y-%m-%dT%H:%M:%SZ') # Example
            # data_for_bq["invoice_date"] = date_obj.strftime('%Y-%m-%d')
            data_for_bq["invoice_date"] = invoice_date_str # Assuming it's already YYYY-MM-DD for BQ DATE
        except ValueError:
            pass

    # Basic validation (example)
    is_valid = True
    errors = []
    if data_for_bq["total_amount"] is not None and data_for_bq["total_amount"] <= 0:
        is_valid = False
        errors.append("Total amount must be positive.")

    return {"isValid": is_valid, "data_for_bq": data_for_bq, "errors": errors}, 200
