import json

def stage4_validation_and_repair(schema: dict) -> dict:
    """Validate cross-layer consistency and repair issues"""
    from pipeline import call_groq, extract_json
    issues = []

    # Check 1: Required top-level keys
    required_keys = ["uiSchema", "apiSchema", "dbSchema", "authSchema"]
    for key in required_keys:
        if key not in schema:
            issues.append(f"MISSING KEY: {key}")

    if len(issues) == len(required_keys):
        # Total failure, can't validate further
        return {"validated": False, "issues": issues, "schema": schema, "repaired": False}

    # Check 2: API endpoints reference valid DB tables
    db_tables = []
    if "dbSchema" in schema and "tables" in schema["dbSchema"]:
        db_tables = [t["name"] for t in schema["dbSchema"]["tables"]]

    api_endpoints = []
    if "apiSchema" in schema and "endpoints" in schema["apiSchema"]:
        api_endpoints = schema["apiSchema"]["endpoints"]

    for ep in api_endpoints:
        if "dbTable" in ep and ep["dbTable"] and ep["dbTable"] not in db_tables:
            issues.append(
                f"API endpoint {ep.get('path')} references non-existent table '{ep['dbTable']}'"
            )

    # Check 3: Auth roles consistent
    auth_roles = []
    if "authSchema" in schema and "roles" in schema["authSchema"]:
        auth_roles = schema["authSchema"]["roles"]

    if "uiSchema" in schema and "pages" in schema["uiSchema"]:
        for page in schema["uiSchema"]["pages"]:
            if (
                page.get("requiredRole")
                and page["requiredRole"] not in auth_roles
                and page["requiredRole"] != "null"
            ):
                issues.append(
                    f"Page '{page.get('name')}' requires role '{page.get('requiredRole')}' not in authSchema roles"
                )

    # If issues found → attempt repair
    if issues:
        repair_prompt = f"""Fix ONLY these specific inconsistencies in the app schema JSON and return corrected valid JSON.
NO explanation. NO markdown. Just raw fixed JSON.

Issues to fix:
{chr(10).join(f"- {i}" for i in issues)}

Original schema:
{json.dumps(schema)}"""

        try:
            raw = call_groq(repair_prompt)
            repaired_schema = extract_json(raw)
            return {
                "validated": False,
                "issues": issues,
                "schema": repaired_schema,
                "repaired": True,
            }
        except Exception as e:
            return {
                "validated": False,
                "issues": issues,
                "schema": schema,
                "repaired": False,
                "repairError": str(e),
            }

    return {
        "validated": True,
        "issues": [],
        "schema": schema,
        "repaired": False,
    }
