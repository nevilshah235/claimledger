"""
JSON Schemas for ADK Agent Structured Output.

Defines schemas for validating agent responses.
"""

# Orchestrator Agent Output Schema
ORCHESTRATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["AUTO_APPROVED", "APPROVED_WITH_REVIEW", "NEEDS_REVIEW", "NEEDS_MORE_DATA", "INSUFFICIENT_DATA", "FRAUD_DETECTED"]
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "reasoning": {
            "type": "string"
        },
        "tool_results": {
            "type": "object",
            "additionalProperties": True
        },
        "requested_data": {
            "type": "array",
            "items": {"type": "string"}
        },
        "human_review_required": {
            "type": "boolean"
        },
        "review_reasons": {
            "type": "array",
            "items": {"type": "string"}
        },
        "contradictions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "fraud_risk": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        }
    },
    "required": ["decision", "confidence", "reasoning", "tool_results", "requested_data", "human_review_required", "review_reasons"]
}

# Document Agent Output Schema
DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_classification": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["receipt", "invoice", "medical_record", "tabular_report", "text_document", "form", "statement", "estimate", "other"]
                },
                "structure": {
                    "type": "string",
                    "enum": ["structured", "semi_structured", "unstructured"]
                },
                "has_tables": {"type": "boolean"},
                "has_line_items": {"type": "boolean"},
                "primary_content_type": {
                    "type": "string",
                    "enum": ["financial", "medical", "legal", "general"]
                }
            },
            "required": ["category", "structure", "has_tables", "has_line_items", "primary_content_type"]
        },
        "extracted_fields": {
            "type": "object",
            "additionalProperties": True
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string"},
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "total": {"type": "number"},
                    "sku": {"type": ["string", "null"]},
                    "category": {"type": ["string", "null"]}
                }
            }
        },
        "tables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "table_index": {"type": "number"},
                    "headers": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "summary": {"type": "string"}
                }
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "extraction_method": {"type": "string"},
                "notes": {"type": "string"}
            },
            "required": ["confidence", "extraction_method"]
        },
        "valid": {"type": "boolean"}
    },
    "required": ["document_classification", "extracted_fields", "metadata", "valid"]
}

# Fraud Agent Output Schema
FRAUD_SCHEMA = {
    "type": "object",
    "properties": {
        "fraud_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "risk_level": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"]
        },
        "indicators": {
            "type": "array",
            "items": {"type": "string"}
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "notes": {"type": "string"},
        "bill_analysis": {
            "type": "object",
            "properties": {
                "extracted_total": {"type": "number"},
                "recommended_amount": {"type": "number"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "total": {"type": "number"},
                            "market_price": {"type": ["number", "null"]},
                            "valid": {"type": "boolean"},
                            "relevant": {"type": "boolean"},
                            "price_valid": {"type": "boolean"},
                            "validation_notes": {"type": "string"}
                        }
                    }
                },
                "claim_amount_match": {"type": "boolean"},
                "document_amount_match": {"type": "boolean"},
                "mismatches": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
    },
    "required": ["fraud_score", "risk_level", "indicators", "confidence"]
}

# Reasoning Agent Output Schema
REASONING_SCHEMA = {
    "type": "object",
    "properties": {
        "final_confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "contradictions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "fraud_risk": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "missing_evidence": {
            "type": "array",
            "items": {"type": "string"}
        },
        "reasoning": {"type": "string"},
        "evidence_gaps": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["final_confidence", "contradictions", "fraud_risk", "missing_evidence", "reasoning", "evidence_gaps"]
}


def validate_against_schema(data: dict, schema: dict) -> tuple[bool, list[str]]:
    """
    Validate data against a JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema definition
        
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    if "required" in schema:
        for field in schema["required"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    # Check type
    if "type" in schema:
        expected_type = schema["type"]
        actual_type = type(data).__name__
        type_map = {
            "dict": "object",
            "list": "array",
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "NoneType": "null"
        }
        if type_map.get(actual_type) != expected_type and expected_type != "object":
            errors.append(f"Type mismatch: expected {expected_type}, got {actual_type}")
    
    # Validate properties
    if "properties" in schema and isinstance(data, dict):
        for prop_name, prop_schema in schema["properties"].items():
            if prop_name in data:
                prop_value = data[prop_name]
                
                # Check enum
                if "enum" in prop_schema:
                    if prop_value not in prop_schema["enum"]:
                        errors.append(f"{prop_name}: value '{prop_value}' not in enum {prop_schema['enum']}")
                
                # Check number range
                if prop_schema.get("type") == "number" and isinstance(prop_value, (int, float)):
                    if "minimum" in prop_schema and prop_value < prop_schema["minimum"]:
                        errors.append(f"{prop_name}: value {prop_value} below minimum {prop_schema['minimum']}")
                    if "maximum" in prop_schema and prop_value > prop_schema["maximum"]:
                        errors.append(f"{prop_name}: value {prop_value} above maximum {prop_schema['maximum']}")
                
                # Recursively validate nested objects
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    nested_valid, nested_errors = validate_against_schema(prop_value, prop_schema)
                    if not nested_valid:
                        errors.extend([f"{prop_name}.{e}" for e in nested_errors])
                
                # Validate array items
                if prop_schema.get("type") == "array" and "items" in prop_schema:
                    if isinstance(prop_value, list):
                        item_schema = prop_schema["items"]
                        for i, item in enumerate(prop_value):
                            if item_schema.get("type") == "object":
                                item_valid, item_errors = validate_against_schema(item, item_schema)
                                if not item_valid:
                                    errors.extend([f"{prop_name}[{i}].{e}" for e in item_errors])
    
    return len(errors) == 0, errors
