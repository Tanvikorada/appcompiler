import json

def stage4_validation_and_repair(schema: dict) -> dict:
    """Validate cross-layer consistency and repair issues"""
    from pipeline import call_groq, extract_json
    issues = []

    if not isinstance(schema, dict):
        return {"validated": False, "issues": ["Schema is not a JSON object"], "schema": schema, "repaired": False}

    def section(key: str) -> dict:
        val = schema.get(key)
        return val if isinstance(val, dict) else {}

    def dict_items(val) -> list:
        # Models sometimes return a dict keyed by name instead of a list
        if isinstance(val, dict):
            val = list(val.values())
        return [v for v in val if isinstance(v, dict)] if isinstance(val, list) else []

    # Check 1: Required top-level keys
    required_keys = ["uiSchema", "apiSchema", "dbSchema", "authSchema"]
    for key in required_keys:
        if not isinstance(schema.get(key), dict):
            issues.append(f"MISSING KEY: {key}")

    if len(issues) == len(required_keys):
        # Total failure, can't validate further
        return {"validated": False, "issues": issues, "schema": schema, "repaired": False}

    # Check 2: API endpoints reference valid DB tables
    db_tables = [t.get("name") for t in dict_items(section("dbSchema").get("tables"))]

    for ep in dict_items(section("apiSchema").get("endpoints")):
        table = ep.get("dbTable")
        if table and isinstance(table, str) and table not in db_tables:
            issues.append(
                f"API endpoint {ep.get('path')} references non-existent table '{table}'"
            )

    # Check 3: Auth roles consistent
    auth_roles = section("authSchema").get("roles")
    if not isinstance(auth_roles, list):
        auth_roles = []

    for page in dict_items(section("uiSchema").get("pages")):
        role = page.get("requiredRole")
        if role and role != "null" and role not in auth_roles:
            issues.append(
                f"Page '{page.get('name')}' requires role '{role}' not in authSchema roles"
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
            if not isinstance(repaired_schema, dict) or not all(isinstance(repaired_schema.get(k), dict) for k in required_keys):
                raise ValueError("Repair returned an incomplete schema")
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
