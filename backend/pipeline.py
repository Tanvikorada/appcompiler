import os
import json
import re
# pyrefly: ignore [missing-import]
from groq import Groq, RateLimitError
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


_use_fallback_directly = False


def call_groq(prompt: str) -> str:
    global _use_fallback_directly
    if _use_fallback_directly:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
        )
        return response.choices[0].message.content

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except RateLimitError as e:
        print(f"Rate limit hit for llama-3.3-70b-versatile. Falling back to llama-3.1-8b-instant. Error: {e}")
        _use_fallback_directly = True
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
        )
        return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response even if wrapped in markdown"""
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting from ```json blocks
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try finding first { to last }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except Exception:
            pass
    raise ValueError(f"Cannot extract JSON from response: {text[:300]}")


def stage1_intent_extraction(user_prompt: str) -> dict:
    """Parse user intent into structured intermediate form"""
    prompt = f"""You are a system analyst. Extract structured intent from this product description.

Return ONLY valid JSON with NO explanation, NO markdown, NO preamble. Just raw JSON.

JSON structure:
{{
  "goal": "one sentence describing the app",
  "entities": [{{"name": "string", "description": "string"}}],
  "userRoles": [{{"role": "string", "permissions": ["string"]}}],
  "features": [{{"name": "string", "description": "string", "priority": "high|medium|low"}}],
  "constraints": ["string"],
  "assumptions": ["string"]
}}

Product description: {user_prompt}"""

    raw = call_groq(prompt)
    return extract_json(raw)


def stage2_system_design(intent: dict) -> dict:
    """Convert intent → app architecture"""
    prompt = f"""You are a software architect. Convert this intent into a system architecture.

Return ONLY valid JSON with NO explanation, NO markdown, NO preamble. Just raw JSON.

JSON structure:
{{
  "pages": [{{
    "name": "string",
    "route": "string",
    "components": ["string"],
    "requiredRole": "string or null"
  }}],
  "apiEndpoints": [{{
    "method": "GET|POST|PUT|DELETE",
    "path": "string",
    "description": "string",
    "requiresAuth": true,
    "requestBody": {{"field": "type"}},
    "responseSchema": {{"field": "type"}}
  }}],
  "dbTables": [{{
    "name": "string",
    "columns": [{{"name": "string", "type": "string", "required": true, "unique": false}}],
    "relations": [{{"type": "hasMany|belongsTo", "table": "string"}}]
  }}],
  "authRules": [{{
    "role": "string",
    "canAccess": ["route"],
    "cannotAccess": ["route"]
  }}]
}}

Intent JSON: {json.dumps(intent)}"""

    raw = call_groq(prompt)
    return extract_json(raw)


def stage3_schema_generation(architecture: dict) -> dict:
    """Generate full UI + API + DB + Auth schemas"""
    prompt = f"""You are a senior engineer. Convert this architecture into a complete app schema.

CRITICAL RULES:
- All API endpoint requestBody fields MUST exist as columns in the corresponding DB table
- All UI form fields MUST map to API endpoint fields
- Return ONLY valid JSON with NO explanation, NO markdown, NO preamble. Just raw JSON.

JSON structure:
{{
  "uiSchema": {{
    "pages": [{{
      "name": "string",
      "route": "string",
      "layout": "string",
      "components": [{{
        "type": "form|table|card|chart|navbar",
        "id": "string",
        "fields": [{{"name": "string", "type": "string", "required": true, "mapsToApi": "endpoint_path"}}],
        "actions": [{{"label": "string", "apiCall": "METHOD /path"}}]
      }}]
    }}]
  }},
  "apiSchema": {{
    "baseUrl": "/api/v1",
    "endpoints": [{{
      "method": "string",
      "path": "string",
      "description": "string",
      "requiresAuth": true,
      "requestBody": {{"field": "type"}},
      "responseSchema": {{"field": "type"}},
      "dbTable": "string"
    }}]
  }},
  "dbSchema": {{
    "tables": [{{
      "name": "string",
      "columns": [{{"name": "string", "type": "VARCHAR|INT|BOOLEAN|TEXT|TIMESTAMP|DECIMAL", "required": true, "unique": false, "primaryKey": false}}],
      "indexes": ["column_name"],
      "relations": [{{"type": "string", "table": "string", "foreignKey": "string"}}]
    }}]
  }},
  "authSchema": {{
    "strategy": "JWT",
    "roles": ["string"],
    "permissionMatrix": {{"role": {{"resource": ["create","read","update","delete"]}}}}
  }}
}}

Architecture JSON: {json.dumps(architecture)}"""

    raw = call_groq(prompt)
    return extract_json(raw)


from validator import stage4_validation_and_repair


def run_pipeline(user_prompt: str) -> dict:
    """Run all 4 stages sequentially"""
    log = {}

    try:
        intent = stage1_intent_extraction(user_prompt)
        log["stage1"] = {"status": "success", "output": intent}
    except Exception as e:
        return {"error": f"Stage 1 failed: {str(e)}", "stage": 1, "log": log}

    try:
        architecture = stage2_system_design(intent)
        log["stage2"] = {"status": "success", "output": architecture}
    except Exception as e:
        return {"error": f"Stage 2 failed: {str(e)}", "stage": 2, "log": log}

    try:
        schema = stage3_schema_generation(architecture)
        log["stage3"] = {"status": "success", "output": schema}
    except Exception as e:
        return {"error": f"Stage 3 failed: {str(e)}", "stage": 3, "log": log}

    try:
        result = stage4_validation_and_repair(schema)
        log["stage4"] = {"status": "success", "output": result}
    except Exception as e:
        return {"error": f"Stage 4 failed: {str(e)}", "stage": 4, "log": log}

    return {
        "success": True,
        "finalSchema": result["schema"],
        "validated": result["validated"],
        "repaired": result["repaired"],
        "issues": result["issues"],
        "pipelineLog": log,
    }
