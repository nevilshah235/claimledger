"""
ADK Document Agent - Analyzes documents using ADK LlmAgent with multimodal support.

Converts the original DocumentAgent to use ADK LlmAgent with Gemini's multimodal capabilities.
"""

import os
from typing import Dict, Any, List
from pathlib import Path

try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


class ADKDocumentAgent:
    """ADK-based agent for document analysis with multimodal support."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, DocumentAgent will use fallback")
            return
        
        if not self.api_key:
            print("⚠️  Warning: GOOGLE_AI_API_KEY or GOOGLE_API_KEY not set")
            return
        
        try:
            # Import ADK tools
            from ..adk_tools import get_adk_tools
            
            # Create ADK LlmAgent with multimodal support
            self.agent = LlmAgent(
                model=self.model_name,
                name="document_agent",
                description="Specialized agent for analyzing insurance claim documents (invoices, receipts, medical records)",
                instruction="""You are an insurance claim document analysis agent.

Your job is to analyze insurance claim documents and extract key information.

**Process:**
1. First, if you need to verify the document authenticity, call verify_document(claim_id, document_path) tool
   - This tool costs $0.10 USDC and handles payment automatically via x402
   - The tool will verify document authenticity and extract structured data
2. Analyze the provided document (PDF, image, etc.) using multimodal capabilities
3. Extract: document type, amount, date, vendor/provider, description
4. Check validity indicators (signatures, stamps, authenticity)
5. Return structured JSON with your findings

**Important:**
- You have access to verify_document tool - use it when you need to verify document authenticity
- The tool handles payment automatically, you don't need to worry about payment processing
- Combine tool results with your own analysis for best results

**Output Format:**
Return a JSON object with:
- document_type: string (invoice, receipt, medical record, etc.)
- amount: number or null
- date: string (YYYY-MM-DD format)
- vendor: string or null
- description: string
- valid: boolean (true if document appears authentic)
- confidence: float (0.0-1.0)
- notes: string (any observations)

Be thorough and accurate in your analysis.""",
                tools=get_adk_tools(),  # Include all ADK tools
            )
        except Exception as e:
            print(f"Failed to initialize ADK DocumentAgent: {e}")
            self.agent = None
    
    async def analyze(
        self,
        claim_id: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze documents for a claim using ADK agent.
        
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
        
        if not self.agent:
            # Fallback to mock analysis
            return self._mock_analysis(claim_id, documents)
        
        # Analyze each document with ADK agent
        results = []
        for doc in documents:
            file_path = doc.get("file_path")
            if not file_path or not Path(file_path).exists():
                continue
            
            try:
                result = await self._analyze_document_with_adk(file_path, claim_id)
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
    
    async def _analyze_document_with_adk(
        self,
        file_path: str,
        claim_id: str
    ) -> Dict[str, Any]:
        """Analyze a single document using ADK agent with multimodal support."""
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
            
            # Create multimodal content for ADK agent
            prompt = f"""Analyze this insurance claim document (Claim ID: {claim_id}) and extract:
1. Document type (invoice, receipt, medical record, etc.)
2. Amount (if applicable)
3. Date
4. Vendor/provider name
5. Description of services/items
6. Validity indicators (signatures, stamps, etc.)

Return a JSON object with:
- document_type: string
- amount: number or null
- date: string (YYYY-MM-DD format)
- vendor: string or null
- description: string
- valid: boolean (true if document appears authentic)
- confidence: float (0.0-1.0)
- notes: string (any observations)"""
            
            # Create content parts with multimodal support
            content_parts = [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=file_data, mime_type=mime_type)
            ]
            
            # Run ADK agent with multimodal input
            from ..adk_runtime import get_adk_runtime
            
            runtime = get_adk_runtime()
            runner = runtime.create_runner(
                app_name="claimledger",
                agent=self.agent
            )
            
            # Create user message with multimodal content
            user_message = types.Content(
                role="user",
                parts=content_parts
            )
            
            # Run agent and collect response
            response_text = ""
            async for event in runner.run_async(
                user_id=f"claim_{claim_id}",
                session_id=f"doc_analysis_{claim_id}",
                new_message=user_message
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                if event.is_final_response():
                    break
            
            # Parse response
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                except:
                    extracted = self._parse_text_response(response_text)
            else:
                extracted = self._parse_text_response(response_text)
            
            return {
                "valid": extracted.get("valid", False),
                "extracted_data": extracted,
                "confidence": extracted.get("confidence", 0.8),
                "notes": extracted.get("notes", "")
            }
            
        except Exception as e:
            print(f"Error in ADK document analysis: {e}")
            return {
                "valid": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        return {
            "document_type": "unknown",
            "amount": None,
            "date": None,
            "vendor": None,
            "description": text[:200],
            "valid": True,
            "confidence": 0.7,
            "notes": text
        }
    
    def _mock_analysis(
        self,
        claim_id: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mock analysis when ADK is not available."""
        return {
            "summary": f"Mock analysis of {len(documents)} document(s)",
            "extracted_data": {
                "document_type": "invoice",
                "amount": 3500.00,
                "date": "2024-01-15",
                "vendor": "Auto Repair Shop",
                "description": "Front bumper repair and replacement"
            },
            "valid": True,
            "confidence": 0.85,
            "verification_id": f"mock_doc_{claim_id}"
        }
