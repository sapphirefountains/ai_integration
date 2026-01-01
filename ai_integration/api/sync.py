import frappe
import json
import requests

@frappe.whitelist()
def export_to_triton():
    """
    Pushes ERPNext Project data to Google Cloud Storage.
    Can be triggered via: /api/method/ai_integration.api.sync.export_to_triton
    """
    # 1. Configuration
    # Ideally, store this in your 'AI Integration Settings' DocType
    gcs_signed_url = frappe.db.get_single_value('AI Integration Settings', 'gcs_sync_url')
    
    if not gcs_signed_url:
        frappe.throw("Please configure the GCS Sync URL in AI Integration Settings.")

    # 2. Fetch Data
    projects = frappe.get_all("Project", 
        fields=["name", "project_name", "status", "expected_end_date", "percent_complete", "notes"],
        filters={"status": ["!=", "Cancelled"]}
    )

    # 3. Format as JSONL
    # No more restrictions: you can use list comprehensions and standard json
    lines = []
    site_url = frappe.utils.get_url()

    for p in projects:
        entry = {
            "title": p.project_name or "Unnamed Project",
            "uri": "{}/app/project/{}".format(site_url, p.name),
            "description": "Status: {}. Completion: {}%. Notes: {}".format(
                p.status, 
                p.percent_complete or 0, 
                p.notes or "No notes"
            ),
            "attributes": {
                "status": p.status,
                "deadline": str(p.expected_end_date) if p.expected_end_date else ""
            }
        }
        lines.append(json.dumps(entry))

    payload = "\n".join(lines)

    # 4. Push to GCS
    try:
        response = requests.put(
            gcs_signed_url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        return {"status": "success", "message": "Pushed {} projects".format(len(projects))}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Triton Sync Error")
        return {"status": "error", "message": str(e)}
