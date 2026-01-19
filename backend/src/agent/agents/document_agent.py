"""
Document Agent - Analyzes documents (invoices, receipts, medical records).

Uses Gemini API for document analysis and data extraction.
"""

import os
from typing import Dict, Any, List
from pathlib import Path

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class DocumentAgent:
    """Specialized agent for document analysis."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.client = None
        
        if self.api_key and GEMINI_AVAILABLE:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Gemini for DocumentAgent: {e}")
                self.client = None
    
    async def analyze(
        self,
        claim_id: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze documents for a claim.
        
        Args:
            claim_id: Claim identifier
            documents: List of document evidence with file_path
            
        Returns:
            {
                "summary": str,
                "extracted_data": dict,
                "valid": bool,
                "confidence": float,
                "verification_id": str
            }
        """
        if not documents:
            return {
                "summary": "No documents provided",
                "extracted_data": {},
                "valid": False,
                "confidence": 0.0,
                "verification_id": None
            }
        
        if not self.client:
            # Fallback to mock analysis - log warning
            import warnings
            warnings.warn(
                f"DocumentAgent: Gemini client not available. API key: {self.api_key[:10] + '...' if self.api_key else 'NOT SET'}. "
                f"Falling back to mock analysis for claim {claim_id}. "
                f"Set GOOGLE_AI_API_KEY environment variable to enable real document analysis.",
                UserWarning
            )
            print(f"⚠️  WARNING: DocumentAgent using mock analysis for claim {claim_id}. Real analysis unavailable.")
            return self._mock_analysis(claim_id, documents)
        
        # Analyze each document with Gemini
        results = []
        for doc in documents:
            file_path = doc.get("file_path")
            if not file_path or not Path(file_path).exists():
                continue
            
            try:
                result = await self._analyze_document(file_path, claim_id)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing document {file_path}: {e}")
                results.append({
                    "valid": False,
                    "error": str(e),
                    "confidence": 0.0
                })
        
        if not results:
            return {
                "summary": "No valid documents could be analyzed",
                "extracted_data": {},
                "valid": False,
                "confidence": 0.0,
                "verification_id": None
            }
        
        # Aggregate results
        valid_count = sum(1 for r in results if r.get("valid", False))
        avg_confidence = sum(r.get("confidence", 0.0) for r in results) / len(results)
        
        # Extract aggregated data
        extracted_data = {}
        for result in results:
            if result.get("extracted_data"):
                extracted_data.update(result["extracted_data"])
        
        return {
            "summary": f"Analyzed {len(results)} document(s). {valid_count} valid.",
            "extracted_data": extracted_data,
            "valid": valid_count > 0,
            "confidence": avg_confidence,
            "verification_id": f"doc_{claim_id}",
            "individual_results": results
        }
    
    async def _analyze_document(
        self,
        file_path: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """Analyze a single document using Gemini."""
        try:
            # Read file
            file_data = Path(file_path).read_bytes()
            file_name = Path(file_path).name
            
            # Determine MIME type
            mime_type = "application/pdf"
            if file_name.endswith((".jpg", ".jpeg")):
                mime_type = "image/jpeg"
            elif file_name.endswith(".png"):
                mime_type = "image/png"
            elif file_name.endswith((".doc", ".docx")):
                mime_type = "application/msword"
            
            # Create enhanced two-stage prompt
            prompt = f"""Analyze this insurance claim document (Claim ID: {claim_id}) in two stages:

STAGE 1 - Document Classification:
First, determine the document structure and type:
- document_category: receipt | invoice | medical_record | tabular_report | text_document | form | statement | estimate | other
- document_structure: structured | semi_structured | unstructured
- has_tables: boolean (true if document contains tabular data)
- has_line_items: boolean (true if document has itemized list of services/products)
- primary_content_type: financial | medical | legal | general

STAGE 2 - Dynamic Field Extraction:
Based on the classification, extract ALL relevant fields from the document. Be comprehensive and extract everything you can identify.

For receipts/invoices:
- vendor_name, vendor_address, vendor_phone, vendor_email, vendor_tax_id
- invoice_number, receipt_number, transaction_id, order_number
- date, time, due_date, service_date
- subtotal, tax_amount, tax_rate, discount, shipping, total_amount, currency
- payment_method, payment_status, payment_reference
- line_items: array of objects with {item_name, description, quantity, unit_price, total, sku, category}
- customer_name, customer_address, customer_phone, customer_email
- billing_address, shipping_address
- notes, terms, conditions, return_policy
- signature, authorized_by

For tabular documents:
- table_count: number of tables found
- tables: array of objects with {table_index, headers: array, rows: array of arrays, summary: string}
- summary_fields: key-value pairs extracted from table summaries
- data_points: important numeric values from tables

For text documents:
- sections: array of objects with {title, content, page_number}
- key_entities: extracted entities (names, dates, amounts, locations, etc.)
- summary: comprehensive document summary
- important_dates: array of dates found
- important_amounts: array of monetary values found

For medical records:
- patient_name, patient_id, date_of_birth, patient_address
- date_of_service, service_period_start, service_period_end
- provider_name, provider_id, provider_license, facility_name, facility_address
- diagnosis_codes: array (ICD codes), procedure_codes: array (CPT codes)
- services: array of objects with {service_name, description, date, cost, code}
- insurance_info: {insurance_name, policy_number, group_number, member_id}
- authorization_numbers: array
- referring_physician, attending_physician

For all document types, also extract:
- document_date, issue_date, expiration_date
- document_id, reference_number
- valid: boolean (true if document appears authentic and complete)
- authenticity_indicators: array of strings (signatures, stamps, watermarks, etc.)
- confidence: float (0.0-1.0, confidence in extraction accuracy)
- extraction_method: string (e.g., "multimodal_vision", "ocr", "structured_parsing")
- notes: string (any observations, missing information, or concerns)

Return a comprehensive JSON object with this structure:
{{
  "document_classification": {{
    "category": "string",
    "structure": "string",
    "has_tables": boolean,
    "has_line_items": boolean,
    "primary_content_type": "string"
  }},
  "extracted_fields": {{
    // All relevant fields as key-value pairs based on document type
    // Include both standard fields (document_type, amount, date, vendor, description)
    // and all additional fields specific to the document category
  }},
  "line_items": [ // if has_line_items is true
    {{
      "item_name": "string",
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "total": number,
      "sku": "string or null",
      "category": "string or null"
    }}
  ],
  "tables": [ // if has_tables is true
    {{
      "table_index": number,
      "headers": ["string"],
      "rows": [["string"]],
      "summary": "string"
    }}
  ],
  "metadata": {{
    "confidence": float,
    "extraction_method": "string",
    "notes": "string"
  }},
  "valid": boolean
}}

IMPORTANT: Extract ALL fields you can identify. Do not limit yourself to only the examples above. Be thorough and comprehensive."""
            
            # Use Gemini to analyze with new API
            from google.genai import types
            
            # Use async client for async operations
            aio_client = self.client.aio
            
            # Create content parts
            contents = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=file_data, mime_type=mime_type)
            ]
            
            # Use async API
            response = await aio_client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            
            # Parse response - new API structure
            if hasattr(response, 'text'):
                text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                text = response.candidates[0].content.parts[0].text
            else:
                text = str(response)
            
            # Try to extract JSON from response
            import json
            import re
            
            # Try to extract JSON from response - handle nested JSON
            # Use a more robust JSON extraction that handles nested structures
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                    # Normalize the response structure
                    extracted = self._normalize_extracted_data(extracted)
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {e}. Attempting fallback parsing.")
                    extracted = self._parse_text_response(text)
            else:
                extracted = self._parse_text_response(text)
            
            # Extract confidence from metadata or top level
            confidence = extracted.get("metadata", {}).get("confidence") or extracted.get("confidence", 0.8)
            notes = extracted.get("metadata", {}).get("notes") or extracted.get("notes", "")
            
            return {
                "valid": extracted.get("valid", False),
                "extracted_data": extracted,
                "confidence": confidence,
                "notes": notes
            }
            
        except Exception as e:
            print(f"Error in document analysis: {e}")
            return {
                "valid": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted data to ensure consistent structure."""
        # If data has document_classification, keep the new structure
        if "document_classification" in data:
            return data
        
        # Otherwise, wrap old structure in new format for backward compatibility
        normalized = {
            "document_classification": {
                "category": data.get("document_type", "unknown"),
                "structure": "semi_structured",  # Default assumption
                "has_tables": False,
                "has_line_items": False,
                "primary_content_type": "financial" if data.get("amount") else "general"
            },
            "extracted_fields": {
                "document_type": data.get("document_type", "unknown"),
                "amount": data.get("amount"),
                "date": data.get("date"),
                "vendor": data.get("vendor"),
                "description": data.get("description", "")
            },
            "metadata": {
                "confidence": data.get("confidence", 0.7),
                "extraction_method": "legacy_format",
                "notes": data.get("notes", "")
            },
            "valid": data.get("valid", True)
        }
        
        # Preserve any additional fields
        for key, value in data.items():
            if key not in ["document_type", "amount", "date", "vendor", "description", "valid", "confidence", "notes"]:
                normalized["extracted_fields"][key] = value
        
        return normalized
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Fallback parsing with new structure
        return {
            "document_classification": {
                "category": "unknown",
                "structure": "unstructured",
                "has_tables": False,
                "has_line_items": False,
                "primary_content_type": "general"
            },
            "extracted_fields": {
                "document_type": "unknown",
                "description": text[:500]  # First 500 chars
            },
            "metadata": {
                "confidence": 0.5,
                "extraction_method": "text_fallback",
                "notes": f"Failed to parse JSON. Raw response: {text[:200]}"
            },
            "valid": False,  # Mark as invalid since we couldn't parse properly
            "confidence": 0.5,
            "notes": text[:500]
        }
    
    def _mock_analysis(
        self,
        claim_id: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return error state when Gemini is not available."""
        return {
            "summary": f"Failed to extract data from {len(documents)} document(s). API unavailable.",
            "extracted_data": {
                "document_classification": {
                    "category": "unknown",
                    "structure": "unknown",
                    "has_tables": False,
                    "has_line_items": False,
                    "primary_content_type": "unknown"
                },
                "extracted_fields": {},
                "metadata": {
                    "confidence": 0.0,
                    "extraction_method": "failed",
                    "notes": "Document extraction failed: Gemini API client not available. Please check GOOGLE_AI_API_KEY environment variable."
                },
                "extraction_failed": True,
                "error": "API_UNAVAILABLE"
            },
            "valid": False,
            "confidence": 0.0,
            "verification_id": None,
            "error": "Document extraction failed: API unavailable"
        }
