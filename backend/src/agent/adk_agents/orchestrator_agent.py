"""
ADK Orchestrator Agent - Main decision-making agent that autonomously calls tools.

This agent orchestrates the claim evaluation by:
1. Calling verification tools (verify_document, verify_image, verify_fraud) autonomously
2. Making decisions based on confidence thresholds
3. Requesting human review when needed
4. Requesting additional data when evidence is insufficient
"""

import json
import os
from typing import Dict, Any, List, Optional
from decimal import Decimal

from ..tools import verify_document, verify_image, verify_fraud

try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


class ADKOrchestratorAgent:
    """ADK-based orchestrator agent that autonomously calls tools and makes decisions."""
    
    # Standard error response format
    @staticmethod
    def create_error_response(error: str, error_type: str = "AGENT_ERROR") -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error: Error message
            error_type: Error type (AGENT_ERROR, API_ERROR, VALIDATION_ERROR, etc.)
            
        Returns:
            Standardized error response dict
        """
        return {
            "success": False,
            "error": error,
            "error_type": error_type,
            "decision": "NEEDS_REVIEW",
            "confidence": 0.0,
            "reasoning": f"Error occurred: {error}",
            "tool_results": {},
            "requested_data": [],
            "human_review_required": True,
            "review_reasons": [f"Agent error: {error}"],
            "auto_settled": False,
            "tx_hash": None,
            "contradictions": [],
            "fraud_risk": 0.5
        }
    
    # Confidence thresholds (enforced in code)
    AUTO_APPROVE_THRESHOLD = 0.70  # >= 70% confidence: auto-approve (with fraud_risk < 0.3 and no contradictions)
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # >= 85% confidence: can approve with human review
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # >= 70% confidence: needs human review
    LOW_CONFIDENCE_THRESHOLD = 0.50  # >= 50% confidence: request more data
    FRAUD_RISK_THRESHOLD = 0.7  # >= 70% fraud risk: FRAUD_DETECTED
    FRAUD_RISK_AUTO_APPROVE_MAX = 0.3  # < 30% fraud risk required for auto-approve
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
        self.agent = None
        
        if not ADK_AVAILABLE:
            print("⚠️  ADK not available, OrchestratorAgent will use fallback")
            return
        
        if not self.api_key:
            print("⚠️  Warning: GOOGLE_AI_API_KEY or GOOGLE_API_KEY not set")
            return
        
        # Ensure GOOGLE_API_KEY is set for ADK (ADK uses GOOGLE_API_KEY internally)
        if not os.getenv("GOOGLE_API_KEY") and self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key
        
        try:
            # Import ADK tools
            from ..adk_tools import get_adk_tools
            
            # Get tools and verify they're created
            tools = get_adk_tools()
            if not tools:
                print("⚠️  WARNING: No ADK tools available! Orchestrator agent will not be able to call verification tools.")
            else:
                tool_names = []
                for tool in tools:
                    # Try to get tool name
                    name = getattr(tool, 'name', None)
                    if not name:
                        # FunctionTool might store the function
                        func = getattr(tool, 'func', None)
                        if func:
                            name = getattr(func, '__name__', 'unknown')
                    tool_names.append(name or 'unknown')
                print(f"   └─ Orchestrator Agent tools: {', '.join(tool_names)}")
            
            # Create ADK LlmAgent with tool-calling capabilities
            # ADK reads GOOGLE_API_KEY from environment automatically
            self.agent = LlmAgent(
                model=self.model_name,
                name="orchestrator_agent",
                description="Main orchestrator agent that evaluates insurance claims by calling verification tools and making decisions",
                instruction="""You are an insurance claim evaluation orchestrator.

**CRITICAL — You MUST use function/tool calls:** Invoke the tools (estimate_repair_cost, cross_check_amounts, validate_claim_data, verify_fraud) via the platform's function/tool-calling API. Do NOT fabricate or guess their results in your response. The system will execute each tool and return real results. Only after you have received the actual results from all four Phase 2 tools, output your final JSON decision.

**Phase 1 (DONE):** verify_document and verify_image have been run. Use the PRE-VERIFIED data. Do NOT call verify_document, verify_image, extract_document_data, or extract_image_data.

**Phase 2 — MANDATORY (invoke each via function/tool call):**
- estimate_repair_cost(claim_id, extracted_data, damage_assessment)
- cross_check_amounts(claim_id, claim_amount, extracted_total, estimated_cost, document_amount, extracted_total_currency, document_amount_currency) — when the document is in INR/Rs/₹, you MUST pass extracted_total_currency and document_amount_currency (e.g. "INR", "Rs") so the tool converts to USD. Claim is always USDC. Never compare claim (USD) to raw rupees (e.g. 40000) as if same currency.
- validate_claim_data(claim_id, claim_amount, extracted_data, damage_assessment, cost_analysis, cross_check_result)
- verify_fraud(claim_id) — you MUST call this; use its fraud_score and risk_level in your reasoning.

**Phase 3:** If amounts match, validate_claim_data recommends PROCEED, verify_fraud shows low risk, and confidence >= 0.70, then call approve_claim(claim_id, amount, recipient).

**Contradictions:** Use the cross_check_amounts tool's "warnings" field as the source for amount-related contradictions. Do not invent contradictions that compare USD to raw INR.

**Output:** After all Phase 2 tools have been invoked and you have their real results, return ONLY valid JSON: {"decision": "...", "confidence": 0.0-1.0, "reasoning": "...", "requested_data": [], "human_review_required": bool, "review_reasons": [], "contradictions": [], "fraud_risk": 0.0-1.0}. Do NOT include "tool_results" — the system records those from your tool calls.""",
                tools=tools,  # Include all ADK tools for autonomous calling
            )
        except Exception as e:
            print(f"Failed to initialize ADK OrchestratorAgent: {e}")
            self.agent = None
    
    async def evaluate_claim(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        claim_description: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate a claim by autonomously calling tools and making decisions.
        
        Args:
            claim_id: Claim identifier
            claim_amount: Claim amount in USDC
            claimant_address: Claimant wallet address
            evidence: List of evidence dicts with file_type and file_path
            claim_description: Optional claim description for relevance checking
            
        Returns:
            {
                "decision": str,
                "confidence": float,
                "reasoning": str,
                "tool_results": dict,
                "requested_data": list,
                "human_review_required": bool,
                "review_reasons": list,
                "auto_settled": bool,
                "tx_hash": str | None
            }
        """
        print(f"\n🤖 [ORCHESTRATOR AGENT] Starting evaluation for claim {claim_id}")
        print(f"   └─ Agent Type: ADK LlmAgent with autonomous tool-calling")
        print(f"   └─ Available Tools: verify_document, verify_image, verify_fraud, approve_claim")
        
        if not self.agent:
            print(f"   └─ ⚠ Agent not available, using fallback evaluation")
            # Fallback to rule-based evaluation
            return await self._fallback_evaluation(claim_id, claim_amount, claimant_address, evidence)
        
        try:
            result = await self._ai_evaluation_with_tools(claim_id, claim_amount, claimant_address, evidence, claim_description)
            print(f"   └─ ✅ Evaluation completed successfully")
            return result
        except ValueError as e:
            if "Missing key inputs argument" in str(e) or "api_key" in str(e).lower():
                print(f"   └─ ❌ API Key Error: {e}")
                print(f"   └─ Checking API key configuration...")
                api_key_set = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY"))
                print(f"   └─ GOOGLE_API_KEY set: {bool(os.getenv('GOOGLE_API_KEY'))}")
                print(f"   └─ GOOGLE_AI_API_KEY set: {bool(os.getenv('GOOGLE_AI_API_KEY'))}")
                print(f"   └─ Agent has API key: {bool(self.api_key)}")
                if not api_key_set:
                    print(f"   └─ ⚠️  Please set GOOGLE_API_KEY or GOOGLE_AI_API_KEY environment variable")
            else:
                print(f"   └─ ❌ Error in ADK orchestrator agent: {e}")
            import traceback
            traceback.print_exc()
            return await self._fallback_evaluation(claim_id, claim_amount, claimant_address, evidence)
        except Exception as e:
            print(f"   └─ ❌ Error in ADK orchestrator agent: {e}")
            import traceback
            traceback.print_exc()
            # Return standardized error response with fallback
            error_response = self.create_error_response(str(e), "AGENT_ERROR")
            fallback_result = await self._fallback_evaluation(claim_id, claim_amount, claimant_address, evidence)
            # Merge fallback with error info
            error_response.update({
                "decision": fallback_result.get("decision", "NEEDS_REVIEW"),
                "confidence": fallback_result.get("confidence", 0.0),
                "reasoning": f"Error occurred, using fallback: {fallback_result.get('reasoning', '')}"
            })
            return error_response
    
    async def _ai_evaluation_with_tools(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        claim_description: str = ""
    ) -> Dict[str, Any]:
        """Use ADK agent to autonomously call tools and make decisions."""
        from ..adk_runtime import get_adk_runtime
        
        # Build evidence context
        print(f"   └─ Building evidence context...")
        evidence_context = self._build_evidence_context(evidence)
        
        documents = [e for e in evidence if e.get("file_type") == "document"]
        images = [e for e in evidence if e.get("file_type") == "image"]
        print(f"   └─ Evidence breakdown: {len(documents)} document(s), {len(images)} image(s)")
        
        # --- Phase 1 (pre-run): verify_document and verify_image so we have doc/image data before the LLM ---
        pre_run_tool_results: Dict[str, Any] = {}
        if documents or images:
            print(f"   └─ Pre-running Phase 1 verify_document/verify_image: {len(documents)} document(s), {len(images)} image(s)")
        for d in documents:
            path = d.get("file_path", "")
            if not path:
                continue
            try:
                r = await verify_document(claim_id, path)
                pre_run_tool_results["verify_document"] = r
            except Exception as e:
                pre_run_tool_results["verify_document"] = {
                    "success": False,
                    "error": str(e),
                    "extracted_data": {},
                    "valid": False,
                    "cost": 0.0,
                }
        for i in images:
            path = i.get("file_path", "")
            if not path:
                continue
            try:
                r = await verify_image(claim_id, path)
                pre_run_tool_results["verify_image"] = r
            except Exception as e:
                pre_run_tool_results["verify_image"] = {
                    "success": False,
                    "error": str(e),
                    "damage_assessment": {},
                    "valid": False,
                    "cost": 0.0,
                }
        vdoc = pre_run_tool_results.get("verify_document") or {}
        vimg = pre_run_tool_results.get("verify_image") or {}
        extracted_data = vdoc.get("extracted_data", {}) if isinstance(vdoc, dict) else {}
        damage_assessment = vimg.get("damage_assessment", {}) if isinstance(vimg, dict) else {}
        doc_valid = vdoc.get("valid", False) if isinstance(vdoc, dict) else False
        img_valid = vimg.get("valid", False) if isinstance(vimg, dict) else False
        # Surface document currency for cross_check_amounts (INR/Rs must be converted to USD)
        ef = (extracted_data or {}).get("extracted_fields") if isinstance(extracted_data, dict) else {}
        if not isinstance(ef, dict):
            ef = {}
        doc_currency = ef.get("currency") or ((extracted_data or {}).get("currency") if isinstance(extracted_data, dict) else None)
        doc_currency_str = str(doc_currency) if doc_currency else "not set (if amounts are in INR/Rs/₹, pass extracted_total_currency and document_amount_currency to cross_check_amounts)"
        if documents or images:
            pre_verified_block = f"""
**PRE-VERIFIED DATA (Phase 1 — already run):**
- verify_document: extracted_data={json.dumps(extracted_data, default=str)}, valid={doc_valid}
- verify_image: damage_assessment={json.dumps(damage_assessment, default=str)}, valid={img_valid}
- Document currency: {doc_currency_str}. When calling cross_check_amounts, you MUST pass extracted_total_currency and document_amount_currency when the document is in INR/Rs/₹ so amounts are converted to USD. Claim is always USDC. Never compare $400 (claim) to 40000 (rupees) as if both were the same currency.

Use the above when calling estimate_repair_cost, cross_check_amounts, validate_claim_data, verify_fraud. Do NOT call verify_document, verify_image, extract_document_data, or extract_image_data.
"""
        else:
            pre_verified_block = """
**PRE-VERIFIED DATA (Phase 1 — already run):** No documents or images. Use empty extracted_data and damage_assessment for Phase 2 tools. Do NOT call verify_document or verify_image.
"""
        
        # Verify tools are available
        from ..adk_tools import get_adk_tools
        tools = get_adk_tools()
        print(f"   └─ Tools registered: {len(tools)} ({', '.join([t.name if hasattr(t, 'name') else getattr(t, '__name__', 'unknown') for t in tools]) if tools else 'none'})")
        if not tools:
            print(f"   └─ ⚠️  WARNING: No tools available! Tool calling will not work.")
        
        prompt = f"""Evaluate this insurance claim.

**STEP 1 — Invoke tools via function/tool calls (do NOT skip, do NOT fabricate results):**
You MUST invoke each of these tools using the platform's function/tool-calling API. The system will execute them and return real results. Do NOT guess or invent tool outputs; do NOT put made-up "tool_results" in your final JSON.

1) estimate_repair_cost(claim_id="{claim_id}", extracted_data=<from PRE-VERIFIED>, damage_assessment=<from PRE-VERIFIED>)
2) cross_check_amounts(claim_id="{claim_id}", claim_amount={float(claim_amount)}, extracted_total=<from extracted_fields>, estimated_cost=<from step 1>, document_amount=<same or from extracted_fields>, extracted_total_currency=<extracted_fields.currency e.g. "INR" or "Rs" when document is in rupees>, document_amount_currency=<same>). Claim is USDC. When the document is in INR/Rs/₹, you MUST pass extracted_total_currency and document_amount_currency so the tool converts to USD. Never compare $400 (claim) to 40000 (rupees) as if both were USD.
3) validate_claim_data(claim_id="{claim_id}", claim_amount={float(claim_amount)}, extracted_data=<from PRE-VERIFIED>, damage_assessment=<from PRE-VERIFIED>, cost_analysis=<from step 1>, cross_check_result=<from step 2>)
4) verify_fraud(claim_id="{claim_id}") — you MUST call this.

**STEP 2 — After you have the real results from all four tools, return your final JSON:**
{{"decision": "AUTO_APPROVED"|"APPROVED_WITH_REVIEW"|"NEEDS_REVIEW"|"NEEDS_MORE_DATA"|"INSUFFICIENT_DATA"|"FRAUD_DETECTED", "confidence": 0.0-1.0, "reasoning": "Brief explanation", "requested_data": [], "human_review_required": true|false, "review_reasons": [], "contradictions": [], "fraud_risk": 0.0-1.0}}
Do NOT include "tool_results" in your JSON; the system records those from your tool calls. For contradictions, use the cross_check_amounts "warnings" (amounts there are in USD after conversion). Never write a contradiction that compares claim (USD) to a raw document number in INR.

---
Claim ID: {claim_id}
Claim Amount: ${float(claim_amount):,.2f} (USDC)
Claimant Address: {claimant_address}
Claim description: {claim_description or "(none)"}

Available Evidence:
{evidence_context}
{pre_verified_block}
**Phase 1 (DONE):** Use PRE-VERIFIED data. Do NOT call verify_document, verify_image, extract_document_data, or extract_image_data.

**Fraud/Evidence:** If evidence is irrelevant, random, or does not support the claim → FRAUD_DETECTED, fraud_risk >= 0.7. Use verify_fraud's real fraud_score and risk_level for fraud_risk. If cross_check_amounts.matches is false after conversion, use its "warnings" for contradictions. Return ONLY the JSON object; no markdown, no code blocks."""
        
        # Create user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )
        
        # Run ADK agent (it will autonomously call tools)
        runtime = get_adk_runtime()
        runner = runtime.create_runner(
            app_name="claimledger",
            agent=self.agent
        )
        
        # Ensure session exists before using it
        user_id = f"claim_{claim_id}"
        session_id = f"orchestrator_{claim_id}"
        await runtime.get_or_create_session(user_id, session_id)
        
        response_text = ""
        tool_results = dict(pre_run_tool_results)  # Phase 1: start with pre-run verify_document/verify_image
        tool_call_count = 0
        pending_tool_calls = {}  # Track tool calls by ID to match with responses
        
        print(f"   └─ Running orchestrator agent with ADK runtime...")
        print(f"      └─ Session: {session_id}")
        print(f"      └─ User: {user_id}")
        print(f"      └─ Tools available: {len(get_adk_tools())} tool(s)")
        
        event_count = 0
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            event_count += 1
            
            # Debug: Log event type and structure (only first few events to avoid spam)
            if event_count <= 3:
                event_type = type(event).__name__
                has_get_function_calls = hasattr(event, 'get_function_calls')
                has_get_function_responses = hasattr(event, 'get_function_responses')
                has_content = hasattr(event, 'content') and event.content is not None
                has_parts = has_content and hasattr(event.content, 'parts') and event.content.parts
                print(f"      └─ Event #{event_count}: {event_type}")
                print(f"         └─ Methods: get_function_calls={has_get_function_calls}, get_function_responses={has_get_function_responses}")
                print(f"         └─ Content: has_content={has_content}, has_parts={has_parts}")
                if has_parts:
                    part_types = [type(p).__name__ for p in event.content.parts]
                    print(f"         └─ Part types: {', '.join(part_types)}")
            
            # Detect function/tool call requests using ADK's get_function_calls()
            if hasattr(event, 'get_function_calls'):
                try:
                    function_calls = event.get_function_calls()
                    if function_calls:
                        for func_call in function_calls:
                            tool_name = func_call.name if hasattr(func_call, 'name') else getattr(func_call, 'function_name', 'unknown')
                            tool_args = func_call.args if hasattr(func_call, 'args') else getattr(func_call, 'arguments', {})
                            call_id = getattr(func_call, 'id', None) or getattr(func_call, 'call_id', None)
                            
                            tool_call_count += 1
                            print(f"      └─ 🔧 Tool Call Request #{tool_call_count}: {tool_name}")
                            print(f"         └─ Arguments: {tool_args}")
                            
                            # Store pending call to match with response
                            if call_id:
                                pending_tool_calls[call_id] = {
                                    'name': tool_name,
                                    'args': tool_args,
                                    'requested': True
                                }
                except Exception as e:
                    print(f"      └─ ⚠ Error getting function calls: {e}")
            
            # Detect function/tool call responses using ADK's get_function_responses()
            if hasattr(event, 'get_function_responses'):
                try:
                    function_responses = event.get_function_responses()
                    if function_responses:
                        for func_response in function_responses:
                            tool_name = func_response.name if hasattr(func_response, 'name') else getattr(func_response, 'function_name', 'unknown')
                            tool_result = func_response.response if hasattr(func_response, 'response') else getattr(func_response, 'result', {})
                            call_id = getattr(func_response, 'id', None) or getattr(func_response, 'call_id', None)
                            
                            print(f"      └─ ✅ Tool Response: {tool_name}")
                            
                            # Store result
                            if isinstance(tool_result, dict):
                                tool_results[tool_name] = tool_result
                                success = tool_result.get('success', False)
                                cost = tool_result.get('cost', 0)
                                status = "✓" if success else "✗"
                                print(f"         └─ {status} Result: success={success}, cost=${cost:.2f}")
                            else:
                                tool_results[tool_name] = {"result": tool_result}
                                print(f"         └─ Result: {str(tool_result)[:100]}")
                except Exception as e:
                    print(f"      └─ ⚠ Error getting function responses: {e}")
            
            # Also check content.parts for function_call and function_response
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Check for function_call in parts
                    if hasattr(part, 'function_call') and part.function_call:
                        func_call = part.function_call
                        tool_name = getattr(func_call, 'name', 'unknown')
                        tool_args = getattr(func_call, 'args', {}) or getattr(func_call, 'arguments', {})
                        
                        if tool_name not in [r.get('name') for r in pending_tool_calls.values()]:
                            tool_call_count += 1
                            print(f"      └─ 🔧 Tool Call (from parts) #{tool_call_count}: {tool_name}")
                            print(f"         └─ Arguments: {tool_args}")
                    
                    # Check for function_response in parts
                    if hasattr(part, 'function_response') and part.function_response:
                        func_resp = part.function_response
                        tool_name = getattr(func_resp, 'name', 'unknown')
                        tool_result = getattr(func_resp, 'response', {}) or getattr(func_resp, 'result', {})
                        
                        if tool_name not in tool_results:
                            print(f"      └─ ✅ Tool Response (from parts): {tool_name}")
                            if isinstance(tool_result, dict):
                                tool_results[tool_name] = tool_result
                            else:
                                tool_results[tool_name] = {"result": tool_result}
                    
                    # Collect text response
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text
            
            if event.is_final_response():
                print(f"      └─ Final response received (event #{event_count})")
                break
        
        print(f"   └─ Total events processed: {event_count}")
        
        print(f"   └─ Agent response received ({len(response_text)} chars)")
        print(f"   └─ Total tool calls detected: {tool_call_count}")
        print(f"   └─ Tool results collected: {len(tool_results)} ({', '.join(tool_results.keys()) if tool_results else 'none'})")
        
        # Fallback: run verify_fraud when the model did not invoke it (e.g. when it returns JSON with fabricated tool_results instead of using function calls)
        if "verify_fraud" not in tool_results:
            print(f"   └─ verify_fraud not in tool results; running verify_fraud(claim_id) as fallback")
            try:
                tool_results["verify_fraud"] = await verify_fraud(claim_id)
            except Exception as e:
                tool_results["verify_fraud"] = {"success": False, "error": str(e), "fraud_score": 0.5, "risk_level": "UNKNOWN", "cost": 0.0}
            print(f"   └─ Fallback verify_fraud completed")
        
        # Validate tool calls
        validation_result = self._validate_tool_calls(tool_results, evidence, claim_id)
        if not validation_result["valid"]:
            print(f"   └─ ⚠️  Tool validation warnings: {', '.join(validation_result['warnings'])}")
        
        # Parse response
        result = self._parse_json_response(response_text)
        
        if not result or "decision" not in result:
            print(f"   └─ ⚠ No valid JSON found in response, using text fallback")
            result = self._parse_text_response(response_text, tool_results)
        
        # Validate against schema
        from ..adk_schemas import validate_against_schema, ORCHESTRATOR_SCHEMA
        is_valid, validation_errors = validate_against_schema(result, ORCHESTRATOR_SCHEMA)
        if not is_valid:
            print(f"   └─ ⚠️  Schema validation errors: {', '.join(validation_errors[:3])}")
            # Fix common issues
            result = self._fix_schema_issues(result, validation_errors)
        
        # Prefer cross_check_amounts.warnings for amount-related contradictions (they use USD after conversion; LLM may have compared to raw INR)
        cc = tool_results.get("cross_check_amounts") or {}
        if isinstance(cc, dict):
            warnings = cc.get("warnings") or []
            if isinstance(warnings, list) and warnings:
                existing = result.get("contradictions") or []
                # Add cross_check warnings and de-dupe, keeping order
                merged = list(dict.fromkeys(existing + [str(w) for w in warnings]))
                result["contradictions"] = merged

        # 5% leniency: drop claim-vs-document amount contradictions when (a) cross_check says within 5%, or
        # (b) the contradiction text itself shows the amounts match (e.g. "≈ $12.0" vs claim $12). Cap fraud when we drop any.
        prev_contradictions = result.get("contradictions") or []
        claim_amt = float(claim_amount)
        result["contradictions"] = [
            c for c in prev_contradictions
            if not (
                self._is_claim_vs_document_amount_contradiction(c)
                and (
                    cc.get("claim_vs_document_within_5_percent")
                    or self._contradiction_amounts_effectively_match(c, claim_amt)
                )
            )
        ]
        dropped_any = len(prev_contradictions) > len(result["contradictions"])
        if dropped_any and float(result.get("fraud_risk", 0.5)) >= 0.3:
            result["fraud_risk"] = 0.25

        # Process decision based on confidence
        agent_confidence = float(result.get("confidence", 0.5))
        
        # Calculate confidence based on tool results
        confidence = self._calculate_confidence_from_results(tool_results, agent_confidence)
        
        # Apply confidence penalty for missing tools
        if not validation_result["valid"]:
            confidence_penalty = validation_result.get("confidence_penalty", 0.0)
            if confidence_penalty > 0:
                confidence = max(0.0, confidence - confidence_penalty)
                print(f"   └─ Confidence penalty applied: -{confidence_penalty:.2%} for missing tools")
        
        # Update result with calculated confidence
        result["confidence"] = confidence
        if confidence != agent_confidence:
            print(f"   └─ Confidence adjusted: {agent_confidence:.2%} → {confidence:.2%} (based on tool results)")
        decision = result.get("decision", "NEEDS_REVIEW")
        contradictions = result.get("contradictions", [])
        fraud_risk = float(result.get("fraud_risk", 0.5))
        
        # Demo: when all evidence is available and extraction succeeded, try to approve for end-to-end settlement
        if os.getenv("DEMO_AUTO_APPROVE") in ("1", "true", "True"):
            if (
                decision != "FRAUD_DETECTED"
                and self._demo_can_auto_approve(tool_results, documents, images, fraud_risk, contradictions)
            ):
                confidence = 0.95
                decision = "AUTO_APPROVED"
                print(f"   └─ [DEMO_AUTO_APPROVE] Promoting to AUTO_APPROVED (extraction OK, fraud low, no contradictions)")
        
        # Enforce decision rules in code (override agent decision if incorrect)
        original_decision = decision
        decision = self._enforce_decision_rules(confidence, fraud_risk, contradictions, decision)
        
        if decision != original_decision:
            print(f"   └─ ⚠️  Decision overridden: {original_decision} → {decision} (enforced by code)")
        
        print(f"\n   └─ 📊 Decision Analysis:")
        print(f"      └─ Decision: {decision} {'(overridden)' if decision != original_decision else ''}")
        print(f"      └─ Confidence: {confidence:.2%}")
        print(f"      └─ Fraud Risk: {fraud_risk:.2f}")
        print(f"      └─ Contradictions: {len(contradictions)}")
        
        # Determine if auto-settlement occurred
        auto_settled = False
        tx_hash = None
        if "approve_claim" in tool_results:
            approve_result = tool_results["approve_claim"]
            if approve_result.get("success"):
                auto_settled = True
                tx_hash = approve_result.get("tx_hash")
                print(f"      └─ ✅ Auto-settlement: Yes (TX: {tx_hash})")
            else:
                print(f"      └─ ❌ Auto-settlement: Failed")
        else:
            print(f"      └─ Auto-settlement: Not attempted")
        
        # Determine human review requirement
        human_review_required = decision in [
            "APPROVED_WITH_REVIEW",
            "NEEDS_REVIEW",
            "NEEDS_MORE_DATA",
            "INSUFFICIENT_DATA",
            "FRAUD_DETECTED"
        ]
        
        # Build review reasons
        review_reasons = []
        if confidence < self.AUTO_APPROVE_THRESHOLD:
            review_reasons.append(f"Confidence {confidence:.2%} below auto-approval threshold ({self.AUTO_APPROVE_THRESHOLD:.2%})")
        if contradictions:
            review_reasons.append(f"{len(contradictions)} contradiction(s) detected")
        if fraud_risk >= 0.3:
            review_reasons.append(f"Fraud risk {fraud_risk:.2f} exceeds threshold (0.3)")
        
        requested_data = result.get("requested_data", [])
        if requested_data:
            review_reasons.append(f"Additional data requested: {', '.join(requested_data)}")
        
        return {
            "decision": decision,
            "confidence": max(0.0, min(1.0, confidence)),
            "reasoning": result.get("reasoning", ""),
            "tool_results": tool_results,
            "requested_data": requested_data,
            "human_review_required": human_review_required,
            "review_reasons": review_reasons,
            "auto_settled": auto_settled,
            "tx_hash": tx_hash,
            "contradictions": contradictions,
            "fraud_risk": fraud_risk
        }
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from agent response with improved robustness."""
        import json
        import re
        
        # Try JSON code blocks first
        patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON code blocks
            r'```\s*(\{.*?\})\s*```',  # Code blocks without json tag
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
            r'\{.*\}',  # Simple JSON
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                json_str = match.group(1) if match.lastindex else match.group(0)
                try:
                    result = json.loads(json_str)
                    if isinstance(result, dict) and "decision" in result:
                        print(f"   └─ ✓ Successfully parsed JSON response")
                        return result
                except json.JSONDecodeError:
                    continue
        
        # If all patterns fail, try to fix common issues
        return self._fix_and_parse_json(response_text)
    
    def _fix_and_parse_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Attempt to fix common JSON issues and parse."""
        import json
        import re
        
        # Try to find JSON-like content
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return None
        
        json_str = json_match.group(0)
        
        # Try to fix common issues
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Try to fix unescaped quotes in strings
        # This is a simple fix - more complex cases might need manual handling
        try:
            result = json.loads(json_str)
            if isinstance(result, dict) and "decision" in result:
                print(f"   └─ ✓ Successfully parsed JSON after fixing common issues")
                return result
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _extract_amount_from_document_result(
        self,
        document_result: Dict[str, Any]
    ) -> Optional[float]:
        """Extract total amount from document extraction result."""
        if not document_result:
            return None
        
        extracted_data = document_result.get("extracted_data", {})
        extracted_fields = extracted_data.get("extracted_fields", {})
        
        # Try different field names
        amount_fields = [
            "total_amount", "grand_total", "final_total",
            "total_liability", "digit_liability"
        ]
        
        for field in amount_fields:
            if field in extracted_fields:
                amount = extracted_fields[field]
                if isinstance(amount, (int, float)):
                    return float(amount)
                elif isinstance(amount, str):
                    # Remove currency symbols and parse
                    import re
                    cleaned = re.sub(r'[₹$,\s]', '', str(amount))
                    try:
                        return float(cleaned)
                    except ValueError:
                        continue
        
        # Try calculating from components
        digit_liability = extracted_fields.get("digit_liability")
        customer_liability = extracted_fields.get("customer_liability")
        
        if digit_liability and customer_liability:
            try:
                return float(digit_liability) + float(customer_liability)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _calculate_confidence_from_results(
        self,
        tool_results: Dict[str, Any],
        agent_confidence: float
    ) -> float:
        """Calculate confidence based on tool results."""
        confidence = agent_confidence
        
        # Boost confidence if all Phase 2 tools called successfully (verify_document/verify_image are in tool_results from pre-run when evidence exists)
        required_tools = ["estimate_repair_cost", "cross_check_amounts", "validate_claim_data", "verify_fraud"]
        called_tools = [tool for tool in required_tools if tool in tool_results]
        tool_completion_rate = len(called_tools) / len(required_tools)
        
        if tool_completion_rate == 1.0:
            confidence = min(1.0, confidence + 0.1)  # Boost by 10%
        elif tool_completion_rate < 0.5:
            confidence = max(0.0, confidence - 0.2)  # Reduce by 20%
        
        # Boost confidence if amounts match
        cross_check = tool_results.get("cross_check_amounts", {})
        if cross_check.get("matches"):
            confidence = min(1.0, confidence + 0.15)  # Boost by 15%
        
        # Reduce confidence if contradictions exist
        contradictions = tool_results.get("reasoning", {}).get("contradictions", [])
        if contradictions:
            confidence = max(0.0, confidence - (len(contradictions) * 0.1))  # Reduce by 10% per contradiction
        
        return max(0.0, min(1.0, confidence))
    
    def _validate_tool_calls(
        self,
        tool_results: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        claim_id: str
    ) -> Dict[str, Any]:
        """
        Validate that required tools were called.
        
        Returns:
            {
                "valid": bool,
                "warnings": List[str],
                "missing_tools": List[str]
            }
        """
        warnings = []
        missing_tools = []
        
        # Check if verify_fraud was called (always required)
        if "verify_fraud" not in tool_results:
            missing_tools.append("verify_fraud")
            warnings.append("verify_fraud was not called (required for all claims)")
        
        # Check if verify_document was called when documents are available
        documents = [e for e in evidence if e.get("file_type") == "document"]
        if documents and "verify_document" not in tool_results:
            missing_tools.append("verify_document")
            warnings.append(f"verify_document was not called but {len(documents)} document(s) available")
        
        # Check if verify_image was called when images are available
        images = [e for e in evidence if e.get("file_type") == "image"]
        if images and "verify_image" not in tool_results:
            missing_tools.append("verify_image")
            warnings.append(f"verify_image was not called but {len(images)} image(s) available")
        
        # Validate tool result structure
        for tool_name, result in tool_results.items():
            if not isinstance(result, dict):
                warnings.append(f"{tool_name} result is not a dict: {type(result)}")
            elif "success" in result and not result.get("success"):
                warnings.append(f"{tool_name} call failed: {result.get('error', 'unknown error')}")
        
        # Calculate confidence penalty for missing tools
        confidence_penalty = 0.0
        if missing_tools:
            # Reduce confidence by 20% for missing critical tools
            confidence_penalty = 0.2
        
        return {
            "valid": len(missing_tools) == 0,
            "warnings": warnings,
            "missing_tools": missing_tools,
            "confidence_penalty": confidence_penalty
        }
    
    def _fix_schema_issues(self, result: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Fix common schema validation issues."""
        # Ensure required fields exist
        if "decision" not in result:
            result["decision"] = "NEEDS_REVIEW"
        if "confidence" not in result:
            result["confidence"] = 0.5
        if "reasoning" not in result:
            result["reasoning"] = ""
        if "tool_results" not in result:
            result["tool_results"] = {}
        if "requested_data" not in result:
            result["requested_data"] = []
        if "human_review_required" not in result:
            result["human_review_required"] = True
        if "review_reasons" not in result:
            result["review_reasons"] = []
        if "contradictions" not in result:
            result["contradictions"] = []
        if "fraud_risk" not in result:
            result["fraud_risk"] = 0.5
        
        # Ensure types are correct
        result["confidence"] = float(result.get("confidence", 0.5))
        result["fraud_risk"] = float(result.get("fraud_risk", 0.5))
        result["confidence"] = max(0.0, min(1.0, result["confidence"]))
        result["fraud_risk"] = max(0.0, min(1.0, result["fraud_risk"]))
        
        return result
    
    def _is_claim_vs_document_amount_contradiction(self, s: str) -> bool:
        """True if the contradiction is about claim amount vs document amount (to drop when within 5%)."""
        if not s or not isinstance(s, str):
            return False
        t = s.lower()
        if "document" not in t or "amount" not in t:
            return False
        return "claim" in t or "differs" in t or "match" in t or "mismatch" in t or "does not" in t

    def _contradiction_amounts_effectively_match(self, s: str, claim_amount: float) -> bool:
        """True if the contradiction text implies the two amounts are the same (e.g. '≈ $12.0' and claim $12)."""
        if not s or not isinstance(s, str) or claim_amount is None:
            return False
        import re
        # "≈ $12.0" or "= $12" or "≈ $12" — the document side in USD
        m = re.search(r'[≈=]\s*\$\s*([\d,]+(?:\.\d+)?)', s)
        if not m:
            return False
        try:
            doc_val = float(m.group(1).replace(',', ''))
        except ValueError:
            return False
        if doc_val <= 0:
            return False
        diff_pct = abs(claim_amount - doc_val) / max(claim_amount, doc_val, 0.01) * 100
        return diff_pct <= 5

    def _demo_can_auto_approve(
        self,
        tool_results: Dict[str, Any],
        documents: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        fraud_risk: float,
        contradictions: List[str],
    ) -> bool:
        """
        Demo helper: True when we have successful extraction for all evidence,
        low fraud risk, and no contradictions. Used with DEMO_AUTO_APPROVE=1
        to drive end-to-end trustless AI settlement.
        """
        if fraud_risk >= 0.3 or len(contradictions) > 0:
            return False
        if not documents and not images:
            return False
        if documents and (tool_results.get("verify_document") or {}).get("success"):
            return True
        if images and (tool_results.get("verify_image") or {}).get("success"):
            return True
        return False
    
    def _enforce_decision_rules(
        self,
        confidence: float,
        fraud_risk: float,
        contradictions: List[str],
        agent_decision: str
    ) -> str:
        """
        Enforce decision rules in code based on thresholds.
        Overrides agent decision if it doesn't match thresholds.
        
        Returns:
            Corrected decision based on thresholds
        """
        # Trust the agent's explicit fraud/reject decision (LLM saw irrelevant or fraudulent evidence)
        if agent_decision == "FRAUD_DETECTED":
            return "FRAUD_DETECTED"

        # Rule 1: FRAUD_DETECTED if fraud_risk >= 0.7 (highest priority)
        if fraud_risk >= self.FRAUD_RISK_THRESHOLD:
            return "FRAUD_DETECTED"
        
        # Validate AUTO_APPROVED conditions - prevent if conditions not met
        auto_approve_conditions_met = (
            confidence >= self.AUTO_APPROVE_THRESHOLD and 
            len(contradictions) == 0 and 
            fraud_risk < self.FRAUD_RISK_AUTO_APPROVE_MAX
        )
        
        # If agent says AUTO_APPROVED but conditions aren't met, override it
        if agent_decision == "AUTO_APPROVED" and not auto_approve_conditions_met:
            # Determine appropriate override based on what condition failed
            if fraud_risk >= self.FRAUD_RISK_AUTO_APPROVE_MAX:
                # High fraud risk - needs review
                if confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                    return "NEEDS_REVIEW"
                else:
                    return "INSUFFICIENT_DATA"
            elif len(contradictions) > 0:
                # Contradictions exist - needs review
                if confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                    return "NEEDS_REVIEW"
                else:
                    return "INSUFFICIENT_DATA"
            elif confidence < self.AUTO_APPROVE_THRESHOLD:
                # Low confidence - determine appropriate decision
                if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                    return "APPROVED_WITH_REVIEW"
                elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                    return "NEEDS_REVIEW"
                elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
                    return "NEEDS_MORE_DATA"
                else:
                    return "INSUFFICIENT_DATA"
        
        # Rule 2: AUTO_APPROVED if confidence >= 70% AND no contradictions AND fraud_risk < 0.3
        if auto_approve_conditions_met:
            return "AUTO_APPROVED"
        
        # Rule 3: APPROVED_WITH_REVIEW if confidence >= 0.85 AND no contradictions
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD and len(contradictions) == 0:
            # Only override if agent decision is lower priority
            if agent_decision not in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW"]:
                return "APPROVED_WITH_REVIEW"
            return agent_decision
        
        # Rule 4: NEEDS_REVIEW if confidence >= 0.70
        if confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            # Only override if agent decision is lower priority
            if agent_decision not in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW", "NEEDS_REVIEW"]:
                return "NEEDS_REVIEW"
            return agent_decision
        
        # Rule 5: NEEDS_MORE_DATA if confidence >= 0.50
        if confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            # Only override if agent decision is lower priority
            if agent_decision not in ["AUTO_APPROVED", "APPROVED_WITH_REVIEW", "NEEDS_REVIEW", "NEEDS_MORE_DATA"]:
                return "NEEDS_MORE_DATA"
            return agent_decision
        
        # Rule 6: INSUFFICIENT_DATA if confidence < 0.50
        return "INSUFFICIENT_DATA"
    
    def _build_evidence_context(self, evidence: List[Dict[str, Any]]) -> str:
        """Build evidence context string with clear file paths for tool calls."""
        if not evidence:
            return "No evidence provided"
        
        context_parts = []
        context_parts.append("Evidence Files Available:")
        for i, ev in enumerate(evidence, 1):
            file_type = ev.get("file_type", "unknown")
            file_path = ev.get("file_path", "unknown")
            context_parts.append(f"  {i}. Type: {file_type.upper()}")
            context_parts.append(f"     File Path: {file_path}")
            context_parts.append(f"     Action Required: Call verify_{file_type}(claim_id, '{file_path}')")
            context_parts.append("")
        
        context_parts.append("IMPORTANT: Use the exact file_path values above when calling verification tools.")
        
        return "\n".join(context_parts)
    
    def _parse_text_response(
        self,
        text: str,
        tool_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse text response when JSON extraction fails."""
        # Extract confidence if mentioned
        import re
        confidence_match = re.search(r'confidence[:\s]+([0-9.]+)', text, re.IGNORECASE)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        
        # Determine decision based on confidence (using enforcement rules)
        decision = self._enforce_decision_rules(confidence, 0.5, [], "NEEDS_REVIEW")
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": text[:500],  # First 500 chars
            "requested_data": [],
            "contradictions": [],
            "fraud_risk": 0.5
        }
    
    async def _fallback_evaluation(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback rule-based evaluation when AI is not available."""
        # Simple rule-based evaluation
        documents = [e for e in evidence if e.get("file_type") == "document"]
        images = [e for e in evidence if e.get("file_type") == "image"]
        
        # Calculate confidence based on available evidence
        confidence = 0.5  # Base confidence
        if documents:
            confidence += 0.2
        if images:
            confidence += 0.2
        if len(documents) + len(images) >= 2:
            confidence += 0.1
        
        confidence = min(1.0, confidence)
        
        # Determine decision
        if confidence >= self.AUTO_APPROVE_THRESHOLD:
            decision = "AUTO_APPROVED"
        elif confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            decision = "APPROVED_WITH_REVIEW"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_REVIEW"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            decision = "NEEDS_MORE_DATA"
        else:
            decision = "INSUFFICIENT_DATA"
        
        requested_data = []
        if not documents:
            requested_data.append("document")
        if not images:
            requested_data.append("image")
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": f"Rule-based evaluation: {len(documents)} document(s), {len(images)} image(s)",
            "tool_results": {},
            "requested_data": requested_data,
            "human_review_required": decision != "AUTO_APPROVED",
            "review_reasons": [f"Confidence {confidence:.2%} below auto-approval threshold"] if confidence < self.AUTO_APPROVE_THRESHOLD else [],
            "auto_settled": False,
            "tx_hash": None,
            "contradictions": [],
            "fraud_risk": 0.5
        }
