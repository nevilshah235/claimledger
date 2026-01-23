"""
ADK Orchestrator - Coordinates ADK agents using ParallelAgent and SequentialAgent.

Replaces the custom MultiAgentOrchestrator with ADK workflow agents.
"""

import os
from typing import Dict, Any, List, Optional
from decimal import Decimal

try:
    from google.adk.agents import ParallelAgent, SequentialAgent, LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    ParallelAgent = None
    SequentialAgent = None
    LlmAgent = None

from ...models import Claim, Evidence
from ..adk_agents.document_agent import ADKDocumentAgent
from ..adk_agents.image_agent import ADKImageAgent
from ..adk_agents.fraud_agent import ADKFraudAgent
from ..adk_agents.reasoning_agent import ADKReasoningAgent
from ..adk_agents.orchestrator_agent import ADKOrchestratorAgent
from ...services.blockchain import get_blockchain_service


class ADKOrchestrator:
    """ADK-based orchestrator for multi-agent claim evaluation."""
    
    def __init__(self):
        if not ADK_AVAILABLE:
            raise ImportError(
                "google-adk is not installed. Install it with: pip install google-adk"
            )
        
        print("🔧 [ORCHESTRATOR] Initializing ADK Orchestrator...")
        print("   └─ Agent Architecture:")
        print("      ├─ Document Agent (ADKDocumentAgent)")
        print("      ├─ Image Agent (ADKImageAgent)")
        print("      ├─ Fraud Agent (ADKFraudAgent)")
        print("      ├─ Reasoning Agent (ADKReasoningAgent)")
        print("      └─ Orchestrator Agent (ADKOrchestratorAgent) - Main decision maker")
        
        # Initialize ADK agents
        print("   └─ Initializing agents...")
        self.document_agent = ADKDocumentAgent()
        print("      ✓ Document Agent initialized")
        
        self.image_agent = ADKImageAgent()
        print("      ✓ Image Agent initialized")
        
        self.fraud_agent = ADKFraudAgent()
        print("      ✓ Fraud Agent initialized")
        
        self.reasoning_agent = ADKReasoningAgent()
        print("      ✓ Reasoning Agent initialized")
        
        self.orchestrator_agent = ADKOrchestratorAgent()  # New orchestrator agent with tool-calling
        if self.orchestrator_agent.agent:
            print("      ✓ Orchestrator Agent initialized (autonomous tool-calling enabled)")
        else:
            print("      ⚠ Orchestrator Agent not available (will use manual coordination)")
        
        self.blockchain = get_blockchain_service()
        print("      ✓ Blockchain service initialized")
        
        # Use orchestrator agent by default (can fallback to manual coordination)
        self.use_orchestrator_agent = True
        
        print("   └─ Orchestration Mode: " + ("Autonomous (Orchestrator Agent)" if self.use_orchestrator_agent and self.orchestrator_agent.agent else "Manual Coordination"))
        print("✅ [ORCHESTRATOR] Initialization complete")
        
        # Note: We'll use manual coordination with ADK runtime
        # rather than ParallelAgent/SequentialAgent directly because
        # our agents are wrapper classes, not pure ADK Agent instances
        # This gives us more control while still using ADK's session management
    
    async def evaluate_claim(
        self,
        claim: Claim,
        evidence: List[Evidence],
        db = None
    ) -> Dict[str, Any]:
        """
        Orchestrate multi-agent evaluation with auto-approval using ADK.
        
        Returns:
            {
                "decision": "AUTO_APPROVED" | "APPROVED_WITH_REVIEW" | "NEEDS_REVIEW" | "NEEDS_MORE_DATA" | "INSUFFICIENT_DATA",
                "confidence": float,
                "summary": str,
                "agent_results": {...},
                "reasoning": {...},
                "auto_settled": bool,
                "tx_hash": str | None,
                "review_reasons": List[str] | None,
                "requested_data": List[str] | None,
                "human_review_required": bool
            }
        """
        # Convert Evidence models to dict format
        evidence_dicts = [
            {
                "file_type": e.file_type,
                "file_path": e.file_path
            }
            for e in evidence
        ]
        
        # Helper to log activity if db is available
        def log(message: str, agent_type: str = "orchestrator", level: str = "INFO", metadata: Dict[str, Any] = None):
            if db:
                try:
                    # Import here to avoid circular dependency
                    from ...api.agent import log_agent_activity
                    log_agent_activity(db, claim.id, agent_type, message, level, metadata)
                    # Note: log_agent_activity already commits, so no need to commit again
                except Exception as e:
                    print(f"Error logging agent activity: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Use orchestrator agent if available (autonomous tool-calling)
        if self.use_orchestrator_agent and self.orchestrator_agent.agent:
            try:
                print(f"\n🎯 [ORCHESTRATOR] Starting autonomous evaluation for claim {claim.id}")
                print(f"   └─ Mode: Orchestrator Agent (Autonomous Tool-Calling)")
                print(f"   └─ Claim Amount: ${float(claim.claim_amount):,.2f}")
                print(f"   └─ Evidence Files: {len(evidence_dicts)} ({', '.join([e.get('file_type', 'unknown') for e in evidence_dicts])})")
                print(f"   └─ Flow: Orchestrator Agent → Tool Calls → Decision")
                
                log("Using orchestrator agent for autonomous tool-calling", "orchestrator", "INFO", {
                    "mode": "autonomous",
                    "evidence_count": len(evidence_dicts),
                    "evidence_types": [e.get('file_type') for e in evidence_dicts]
                })
                
                result = await self.orchestrator_agent.evaluate_claim(
                    claim.id,
                    claim.claim_amount,
                    claim.claimant_address,
                    evidence_dicts
                )
                
                decision = result.get('decision', 'UNKNOWN')
                confidence = result.get("confidence", 0.0)
                tool_results = result.get("tool_results", {})
                
                print(f"\n✅ [ORCHESTRATOR] Autonomous evaluation completed")
                print(f"   └─ Decision: {decision}")
                print(f"   └─ Confidence: {confidence:.2%}")
                print(f"   └─ Tools Called: {len(tool_results)} ({', '.join(tool_results.keys()) if tool_results else 'none'})")
                if result.get("auto_settled"):
                    print(f"   └─ Auto-Settled: Yes (TX: {result.get('tx_hash', 'N/A')})")
                if result.get("requested_data"):
                    print(f"   └─ Requested Data: {', '.join(result['requested_data'])}")
                
                log(f"Orchestrator agent completed with decision: {decision}", 
                    "orchestrator", "INFO", {
                        "decision": decision,
                        "confidence": confidence,
                        "tools_called": list(tool_results.keys()),
                        "auto_settled": result.get("auto_settled", False)
                    })
                
                # Generate summary - ensure we use the correct claim object
                # Double-check claim ID matches to prevent data mismatch
                assert claim.id == claim_id, f"Claim ID mismatch: expected {claim_id}, got {claim.id}"
                summary = await self._generate_summary_from_result(claim, result)
                # Sanitize summary to remove any technical details that might have leaked through
                summary = self._sanitize_summary(summary, claim.id)
                
                # Print final flow summary for autonomous mode
                print(f"\n📋 [ORCHESTRATOR] Final Flow Summary:")
                print(f"   └─ Execution Path: Autonomous (Orchestrator Agent)")
                print(f"   └─ Tools Called: {len(tool_results)} ({', '.join(tool_results.keys()) if tool_results else 'none'})")
                print(f"   └─ Final Decision: {decision}")
                print(f"   └─ Confidence: {confidence:.2%}")
                if result.get("requested_data"):
                    print(f"   └─ Requested Data: {', '.join(result['requested_data'])}")
                if result.get("auto_settled") and result.get("tx_hash"):
                    print(f"   └─ Settlement: Auto-settled (TX: {result['tx_hash']})")
                elif decision == "AUTO_APPROVED":
                    print(f"   └─ Settlement: Auto-approved (pending settlement)")
                else:
                    print(f"   └─ Settlement: Requires human review")
                
                return {
                    "decision": result["decision"],
                    "confidence": result["confidence"],
                    "summary": summary,
                    "agent_results": result.get("tool_results", {}),
                    "reasoning": result.get("reasoning", ""),
                    "auto_settled": result.get("auto_settled", False),
                    "tx_hash": result.get("tx_hash"),
                    "review_reasons": result.get("review_reasons", []),
                    "requested_data": result.get("requested_data", []),
                    "human_review_required": result.get("human_review_required", False),
                    "fraud_risk": result.get("fraud_risk", 0.5),
                    "contradictions": result.get("contradictions", [])
                }
            except Exception as e:
                print(f"\n❌ [ORCHESTRATOR] Error in orchestrator agent: {e}")
                print(f"   └─ Falling back to manual coordination")
                log(f"Error in orchestrator agent, falling back to manual coordination: {str(e)}", 
                    "orchestrator", "WARNING", {"error": str(e), "fallback": "manual_coordination"})
                print(f"Error in orchestrator agent, falling back to manual coordination: {e}")
                import traceback
                traceback.print_exc()
                # Fall through to manual coordination
        
        # Fallback: Manual coordination (original approach)
        print(f"\n🎯 [ORCHESTRATOR] Starting manual coordination for claim {claim.id}")
        print(f"   └─ Mode: Manual Coordination (Parallel → Sequential)")
        print(f"   └─ Flow: Document/Image (parallel) → Fraud (sequential) → Reasoning → Decision")
        
        log("Starting manual agent coordination", "orchestrator", "INFO", {
            "mode": "manual_coordination",
            "evidence_count": len(evidence_dicts)
        })
        
        # Run agents in parallel where possible (document and image)
        print(f"\n📊 [ORCHESTRATOR] Phase 1: Parallel Agent Execution")
        agent_results = await self._run_agents_parallel(
            claim.id,
            claim.claim_amount,
            claim.claimant_address,
            evidence_dicts,
            db=db
        )
        
        print(f"   └─ Completed agents: {', '.join(agent_results.keys())}")
        for agent_type, result in agent_results.items():
            if result and not result.get("error"):
                conf = result.get("confidence", 0.0)
                print(f"      • {agent_type.capitalize()}: {conf:.2%} confidence")
            else:
                print(f"      • {agent_type.capitalize()}: ERROR")
        
        log(f"Completed parallel agent execution. Results from: {', '.join(agent_results.keys())}", 
            "orchestrator", "INFO", {
                "completed_agents": list(agent_results.keys()),
                "agent_confidences": {k: v.get("confidence", 0.0) for k, v in agent_results.items() if v and not v.get("error")}
            })
        
        # Reasoning agent correlates and analyzes
        print(f"\n🧠 [ORCHESTRATOR] Phase 2: Reasoning & Correlation")
        try:
            log("Starting reasoning agent to correlate results", "reasoning", "INFO", {
                "input_agents": list(agent_results.keys())
            })
            reasoning_result = await self.reasoning_agent.reason(
                claim.id,
                claim.claim_amount,
                agent_results
            )
            
            final_conf = reasoning_result.get('final_confidence', 0)
            fraud_risk = reasoning_result.get('fraud_risk', 0)
            contradictions = reasoning_result.get("contradictions", [])
            
            print(f"   └─ Final Confidence: {final_conf:.2%}")
            print(f"   └─ Fraud Risk: {fraud_risk:.2f}")
            print(f"   └─ Contradictions: {len(contradictions)}")
            if contradictions:
                for c in contradictions:
                    print(f"      • {c}")
            
            log(f"Reasoning agent completed. Final confidence: {final_conf:.2%}", 
                "reasoning", "INFO", {
                    "confidence": final_conf,
                    "fraud_risk": fraud_risk,
                    "contradictions": contradictions,
                    "contradiction_count": len(contradictions)
                })
        except Exception as e:
            print(f"   └─ ERROR: {e}")
            print(f"   └─ Using fallback rule-based reasoning")
            log(f"Error in reasoning agent, using fallback: {str(e)}", "reasoning", "WARNING", {"error": str(e)})
            print(f"Error in reasoning agent: {e}")
            # Fallback to rule-based reasoning
            reasoning_result = self._fallback_reasoning(agent_results)
        
        # Generate comprehensive summary
        summary = await self._generate_summary(
            claim, agent_results, reasoning_result
        )
        
        # Decision logic with new thresholds
        confidence = reasoning_result["final_confidence"]
        contradictions = reasoning_result.get("contradictions", [])
        fraud_risk = reasoning_result.get("fraud_risk", 1.0)
        
        # Helper to log activity if db is available
        def log(message: str, agent_type: str = "orchestrator", level: str = "INFO", metadata: Dict[str, Any] = None):
            if db:
                try:
                    # Import here to avoid circular dependency
                    from ...api.agent import log_agent_activity
                    log_agent_activity(db, claim.id, agent_type, message, level, metadata)
                    # Note: log_agent_activity already commits, so no need to commit again
                except Exception as e:
                    print(f"Error logging agent activity: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Determine decision based on confidence thresholds (with FRAUD_DETECTED support)
        print(f"\n⚖️  [ORCHESTRATOR] Phase 3: Decision Making")
        print(f"   └─ Evaluating thresholds:")
        print(f"      • Confidence: {confidence:.2%} (threshold: 95% for auto-approve)")
        print(f"      • Contradictions: {len(contradictions)} (threshold: 0 for auto-approve)")
        print(f"      • Fraud Risk: {fraud_risk:.2f} (threshold: <0.3 for auto-approve, >=0.7 for fraud)")
        
        # Decision enforcement: Check fraud first
        if fraud_risk >= 0.7:
            decision = "FRAUD_DETECTED"
            print(f"   └─ 🚨 Decision: FRAUD_DETECTED (fraud_risk >= 0.7)")
            log(f"High fraud risk ({fraud_risk:.2f}). Fraud detected.", 
                "orchestrator", "WARNING", {
                    "fraud_risk": fraud_risk,
                    "decision_path": "fraud_detected"
                })
            auto_settled = False
            tx_hash = None
        elif confidence >= 0.95 and len(contradictions) == 0 and fraud_risk < 0.3:
            decision = "AUTO_APPROVED"
            print(f"   └─ ✅ Decision: AUTO_APPROVED (all thresholds met)")
            log(f"High confidence ({confidence:.2%}) with no contradictions and low fraud risk. Auto-approving claim.", 
                "orchestrator", "INFO", {
                    "confidence": confidence,
                    "fraud_risk": fraud_risk,
                    "contradictions": len(contradictions),
                    "decision_path": "high_confidence_auto_approve"
                })
            auto_settled = True
            log("Initiating automatic settlement on blockchain", "orchestrator", "INFO")
            print(f"   └─ Initiating blockchain settlement...")
            settlement_result = await self._auto_settle(claim, reasoning_result)
            tx_hash = settlement_result.get("tx_hash")
            if tx_hash:
                print(f"   └─ ✅ Settlement successful: {tx_hash}")
                log(f"Auto-settlement successful. Transaction hash: {tx_hash}", "orchestrator", "INFO", {"tx_hash": tx_hash})
            else:
                print(f"   └─ ❌ Settlement failed")
                log("Auto-settlement failed - no transaction hash returned", "orchestrator", "WARNING")
        elif confidence >= 0.85 and len(contradictions) == 0:
            decision = "APPROVED_WITH_REVIEW"
            print(f"   └─ ✅ Decision: APPROVED_WITH_REVIEW (confidence >= 85%, no contradictions)")
            log(f"Approved with review required. Confidence: {confidence:.2%}", 
                "orchestrator", "INFO", {
                    "confidence": confidence,
                    "decision_path": "approved_with_review"
                })
            auto_settled = False
            tx_hash = None
        elif confidence >= 0.70:
            decision = "NEEDS_REVIEW"
            print(f"   └─ ⚠️  Decision: NEEDS_REVIEW (confidence >= 70%)")
            log(f"Claim needs manual review. Confidence: {confidence:.2%}", 
                "orchestrator", "INFO", {
                    "confidence": confidence,
                    "contradictions": len(contradictions),
                    "decision_path": "needs_review"
                })
            auto_settled = False
            tx_hash = None
        elif confidence >= 0.50:
            decision = "NEEDS_MORE_DATA"
            print(f"   └─ ⚠️  Decision: NEEDS_MORE_DATA (confidence >= 50%)")
            log(f"Insufficient confidence ({confidence:.2%}). Requesting additional data.", 
                "orchestrator", "INFO", {
                    "confidence": confidence,
                    "decision_path": "needs_more_data"
                })
            auto_settled = False
            tx_hash = None
        else:
            decision = "INSUFFICIENT_DATA"
            print(f"   └─ ❌ Decision: INSUFFICIENT_DATA (confidence < 50%)")
            log(f"Very low confidence ({confidence:.2%}). Insufficient data to process claim.", 
                "orchestrator", "WARNING", {
                    "confidence": confidence,
                    "decision_path": "insufficient_data"
                })
            auto_settled = False
            tx_hash = None
        
        print(f"\n✅ [ORCHESTRATOR] Evaluation complete: {decision}")
        
        # Determine requested data
        requested_data = reasoning_result.get("missing_evidence", [])
        if not requested_data and decision in ["NEEDS_MORE_DATA", "INSUFFICIENT_DATA"]:
            # Request missing evidence types
            if "document" not in agent_results:
                requested_data.append("document")
            if "image" not in agent_results:
                requested_data.append("image")
        
        # Print final flow summary
        print(f"\n📋 [ORCHESTRATOR] Final Flow Summary:")
        print(f"   └─ Execution Path: Manual Coordination")
        print(f"   └─ Agents Executed: {', '.join(agent_results.keys())}")
        print(f"   └─ Final Decision: {decision}")
        print(f"   └─ Confidence: {confidence:.2%}")
        if requested_data:
            print(f"   └─ Requested Data: {', '.join(requested_data)}")
        if auto_settled and tx_hash:
            print(f"   └─ Settlement: Auto-settled (TX: {tx_hash})")
        elif decision == "AUTO_APPROVED":
            print(f"   └─ Settlement: Auto-approved (pending settlement)")
        else:
            print(f"   └─ Settlement: Requires human review")
        
        return {
            "decision": decision,
            "confidence": confidence,
            "summary": summary,
            "agent_results": agent_results,
            "reasoning": reasoning_result,
            "auto_settled": auto_settled,
            "tx_hash": tx_hash,
            "review_reasons": self._get_review_reasons(reasoning_result),
            "requested_data": requested_data,
            "human_review_required": decision != "AUTO_APPROVED"
        }
    
    async def _run_agents_parallel(
        self,
        claim_id: str,
        claim_amount: Decimal,
        claimant_address: str,
        evidence: List[Dict[str, Any]],
        db = None
    ) -> Dict[str, Any]:
        """Run specialized agents in parallel using asyncio (ADK agents handle their own sessions)."""
        import asyncio
        
        # Helper to log activity if db is available
        def log(message: str, agent_type: str = "orchestrator", level: str = "INFO", metadata: Dict[str, Any] = None):
            if db:
                try:
                    from ...api.agent import log_agent_activity
                    log_agent_activity(db, claim_id, agent_type, message, level, metadata)
                except Exception as e:
                    print(f"Error logging: {e}")
        
        # Find evidence by type
        documents = [e for e in evidence if e.get("file_type") == "document"]
        images = [e for e in evidence if e.get("file_type") == "image"]
        
        # Run document and image agents in parallel
        agent_results = {}
        tasks = []
        
        if documents:
            print(f"   └─ 📄 Document Agent: Starting analysis of {len(documents)} document(s)")
            log(f"Starting document agent analysis for {len(documents)} document(s)", "document", "INFO", {"file_count": len(documents)})
            tasks.append(("document", self.document_agent.analyze(claim_id, documents)))
        if images:
            print(f"   └─ 🖼️  Image Agent: Starting analysis of {len(images)} image(s)")
            log(f"Starting image agent analysis for {len(images)} image(s)", "image", "INFO", {"file_count": len(images)})
            tasks.append(("image", self.image_agent.analyze(claim_id, images)))
        
        if tasks:
            print(f"   └─ Running {len(tasks)} agent(s) in parallel...")
            # Wait for document/image agents to complete in parallel
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # Build results dict
            for i, (agent_type, _) in enumerate(tasks):
                if isinstance(results[i], Exception):
                    print(f"   └─ ❌ {agent_type.capitalize()} Agent: ERROR - {str(results[i])}")
                    log(f"Error in {agent_type} agent: {str(results[i])}", agent_type, "ERROR", {"error": str(results[i])})
                    print(f"Error in {agent_type} agent: {results[i]}")
                    agent_results[agent_type] = {
                        "error": str(results[i]),
                        "valid": False,
                        "confidence": 0.0
                    }
                else:
                    result = results[i]
                    confidence = result.get("confidence", 0.0)
                    valid = result.get("valid", False)
                    status = "✓" if valid else "✗"
                    print(f"   └─ {status} {agent_type.capitalize()} Agent: Completed ({confidence:.2%} confidence)")
                    log(f"{agent_type.capitalize()} agent completed. Confidence: {confidence:.2%}", 
                        agent_type, "INFO", {"confidence": confidence, "valid": valid})
                    agent_results[agent_type] = result
        
        # Now run fraud agent with access to other results (sequential after parallel)
        print(f"\n   └─ 🛡️  Fraud Agent: Starting analysis (has access to {len(agent_results)} previous result(s))")
        try:
            log("Starting fraud detection agent", "fraud", "INFO", {
                "input_agent_results": list(agent_results.keys())
            })
            fraud_result = await self.fraud_agent.analyze(
                claim_id,
                claim_amount,
                claimant_address,
                evidence,
                agent_results
            )
            fraud_score = fraud_result.get("fraud_score", 0.5)
            risk_level = fraud_result.get("risk_level", "UNKNOWN")
            indicators = fraud_result.get("indicators", [])
            print(f"   └─ ✓ Fraud Agent: Completed (Risk: {risk_level}, Score: {fraud_score:.2f})")
            if indicators:
                print(f"      └─ Indicators: {', '.join(indicators[:3])}{'...' if len(indicators) > 3 else ''}")
            log(f"Fraud agent completed. Risk level: {risk_level}, Score: {fraud_score:.2f}", 
                "fraud", "INFO", {
                    "fraud_score": fraud_score,
                    "risk_level": risk_level,
                    "indicators": indicators
                })
            agent_results["fraud"] = fraud_result
        except Exception as e:
            print(f"   └─ ❌ Fraud Agent: ERROR - {str(e)}")
            log(f"Error in fraud agent: {str(e)}", "fraud", "ERROR", {"error": str(e)})
            print(f"Error in fraud agent: {e}")
            agent_results["fraud"] = {
                "error": str(e),
                "fraud_score": 0.5,  # Default to medium risk on error
                "risk_level": "MEDIUM",
                "indicators": ["Agent error"],
                "confidence": 0.5
            }
        
        return agent_results
    
    async def _generate_summary(
        self,
        claim: Claim,
        agent_results: Dict[str, Any],
        reasoning_result: Dict[str, Any]
    ) -> str:
        """Generate comprehensive summary for auto-approval."""
        try:
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return self._generate_template_summary(claim, agent_results, reasoning_result)
            
            import google.genai as genai
            client = genai.Client(api_key=api_key)
            model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
            
            # Map technical decision codes to user-friendly terms
            decision_map = {
                'AUTO_APPROVED': 'Approved',
                'APPROVED_WITH_REVIEW': 'Approved (pending review)',
                'NEEDS_REVIEW': 'Needs review',
                'NEEDS_MORE_DATA': 'Needs more information',
                'INSUFFICIENT_DATA': 'Insufficient information',
                'FRAUD_DETECTED': 'Rejected',
                'REJECTED': 'Rejected'
            }
            
            prompt = f"""Generate a clear, user-friendly summary for this insurance claim evaluation.

IMPORTANT: Do NOT include technical details like:
- Full claim IDs or UUIDs
- Wallet addresses or blockchain addresses
- Internal status codes (like INSUFFICIENT_DATA, EVALUATING, etc.)
- Technical metrics (confidence percentages, thresholds, fraud risk scores)
- Internal system details (tool calls, agent names, contradictions)

Instead, write in plain language that a claimant or insurer can understand.

Claim Information:
- Claim Amount: ${float(claim.claim_amount):,.2f}

Agent Analysis Results:
{self._format_agent_results(agent_results)}

Provide a clear, professional summary in plain language. Focus on:
- What was evaluated
- What decision was made
- What (if anything) is needed next
- Any important findings

Write as if explaining to a non-technical user."""
            
            # Use async API
            aio_client = client.aio
            response = await aio_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            # Parse response
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text
            else:
                return str(response)
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            return self._generate_template_summary(claim, agent_results, reasoning_result)
    
    def _generate_template_summary(
        self,
        claim: Claim,
        agent_results: Dict[str, Any],
        reasoning_result: Dict[str, Any]
    ) -> str:
        """Generate template-based summary when AI is not available."""
        summary_parts = [
            f"**Claim Evaluation Summary**",
            "",
            f"**Claim Amount:** ${float(claim.claim_amount):,.2f}",
            "",
            "**Evaluation Results:**"
        ]
        
        if "document" in agent_results:
            doc_result = agent_results["document"]
            status = 'Verified' if doc_result.get('valid') else 'Could not verify'
            summary_parts.append(f"- Document: {status}")
            if doc_result.get("extracted_data"):
                data = doc_result["extracted_data"]
                if data.get('amount'):
                    summary_parts.append(f"  Amount found: ${data.get('amount', 0):,.2f}")
        
        if "image" in agent_results:
            img_result = agent_results["image"]
            status = 'Verified' if img_result.get('valid') else 'Could not verify'
            summary_parts.append(f"- Image: {status}")
            if img_result.get("damage_assessment"):
                assessment = img_result["damage_assessment"]
                damage_type = assessment.get('damage_type', 'unknown')
                summary_parts.append(f"  Damage type: {damage_type.replace('_', ' ').title()}")
        
        if "fraud" in agent_results:
            fraud_result = agent_results["fraud"]
            risk_level = fraud_result.get('risk_level', 'UNKNOWN')
            # Convert technical risk levels to user-friendly terms
            risk_map = {
                'LOW': 'Low risk',
                'MEDIUM': 'Medium risk',
                'HIGH': 'High risk',
                'UNKNOWN': 'Unable to assess'
            }
            user_friendly_risk = risk_map.get(risk_level, risk_level)
            summary_parts.append(f"- Fraud assessment: {user_friendly_risk}")
        
        summary_parts.append("")
        reasoning = reasoning_result.get('reasoning', 'Pending review')
        if not reasoning or reasoning == 'Pending review':
            reasoning = 'Evaluation completed. Review required.'
        summary_parts.append(f"**Assessment:** {reasoning}")
        
        summary = "\n".join(summary_parts)
        return self._sanitize_summary(summary, claim.id)
    
    def _sanitize_summary(self, summary: str, correct_claim_id: str) -> str:
        """Remove technical details and ensure correct claim ID is used."""
        if not summary:
            return summary
        
        import re
        
        # Remove full UUIDs (but keep short claim IDs like #a9297b57)
        # Pattern: full UUIDs like a9297b57-6f79-4bb9-9583-cd708361c2d0
        uuid_pattern = r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'
        summary = re.sub(uuid_pattern, '', summary, flags=re.IGNORECASE)
        
        # Remove full wallet addresses (0x followed by 40 hex characters)
        wallet_pattern = r'\b0x[0-9a-f]{40}\b'
        summary = re.sub(wallet_pattern, '', summary, flags=re.IGNORECASE)
        
        # Remove technical status codes
        technical_statuses = [
            'INSUFFICIENT_DATA', 'EVALUATING', 'AWAITING_DATA', 
            'NEEDS_MORE_DATA', 'AUTO_APPROVED', 'APPROVED_WITH_REVIEW',
            'FRAUD_DETECTED', 'NEEDS_REVIEW'
        ]
        for status in technical_statuses:
            summary = summary.replace(status, '')
            summary = summary.replace(status.replace('_', ' '), '')
        
        # Remove confidence percentages and thresholds
        summary = re.sub(r'\b\d+\.\d+%\s*(?:confidence|threshold|below|above)', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'confidence\s*level\s*[:\-]?\s*\d+\.?\d*%?', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'auto-approval\s*threshold\s*[:\-]?\s*\(?\d+\.?\d*%?\)?', '', summary, flags=re.IGNORECASE)
        
        # Remove technical phrases
        technical_phrases = [
            'No tools were called',
            'tools were called',
            'specific data was requested',
            'tool calls',
            'agent results',
            'tool_results'
        ]
        for phrase in technical_phrases:
            summary = summary.replace(phrase, '')
            summary = summary.replace(phrase.title(), '')
        
        # Clean up extra whitespace
        summary = re.sub(r'\s+', ' ', summary)
        summary = re.sub(r'\n\s*\n\s*\n+', '\n\n', summary)
        summary = summary.strip()
        
        # Ensure we don't have wrong claim ID in summary
        # Extract short claim ID (first 8 chars)
        short_claim_id = correct_claim_id[:8] if len(correct_claim_id) >= 8 else correct_claim_id
        # If summary mentions a different claim ID, remove it
        claim_id_pattern = r'#?[0-9a-f]{8}'
        found_ids = re.findall(claim_id_pattern, summary, flags=re.IGNORECASE)
        for found_id in found_ids:
            clean_id = found_id.replace('#', '').lower()
            if clean_id != short_claim_id.lower():
                # Remove references to wrong claim ID
                summary = re.sub(rf'\b{re.escape(found_id)}\b', '', summary, flags=re.IGNORECASE)
        
        return summary
    
    async def _auto_settle(
        self,
        claim: Claim,
        reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically settle approved claim."""
        try:
            tx_hash = await self.blockchain.approve_claim(
                claim_id=claim.id,
                amount=claim.claim_amount,
                recipient=claim.claimant_address
            )
            return {"tx_hash": tx_hash}
        except Exception as e:
            print(f"Error in auto-settlement: {e}")
            return {"tx_hash": None, "error": str(e)}
    
    def _fallback_reasoning(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based reasoning when reasoning agent fails."""
        # Calculate average confidence from available agents
        confidences = []
        fraud_risks = []
        
        for agent_type, result in agent_results.items():
            if result and not result.get("error"):
                if "confidence" in result:
                    confidences.append(result["confidence"])
                if agent_type == "fraud" and "fraud_score" in result:
                    fraud_risks.append(result["fraud_score"])
        
        # Average confidence, default to 0.5 if no results
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        fraud_risk = sum(fraud_risks) / len(fraud_risks) if fraud_risks else 0.5
        
        # Check for contradictions (simple rule-based)
        contradictions = []
        if "document" in agent_results and "image" in agent_results:
            doc_result = agent_results["document"]
            img_result = agent_results["image"]
            if not doc_result.get("error") and not img_result.get("error"):
                doc_amount = doc_result.get("extracted_data", {}).get("amount", 0)
                img_cost = img_result.get("damage_assessment", {}).get("estimated_cost", 0)
                if doc_amount > 0 and img_cost > 0:
                    diff = abs(doc_amount - img_cost) / max(doc_amount, img_cost)
                    if diff > 0.2:  # 20% difference
                        contradictions.append("Amount mismatch between document and image")
        
        return {
            "final_confidence": avg_confidence,
            "contradictions": contradictions,
            "fraud_risk": fraud_risk,
            "missing_evidence": [],
            "reasoning": "Rule-based fallback reasoning"
        }
    
    def _get_review_reasons(self, reasoning_result: Dict[str, Any]) -> List[str]:
        """Extract reasons why claim needs manual review."""
        reasons = []
        confidence = reasoning_result.get("final_confidence", 0)
        if confidence < 0.95:
            reasons.append(f"Confidence {confidence:.2%} below 95% threshold")
        
        contradictions = reasoning_result.get("contradictions", [])
        if contradictions:
            reasons.append(f"{len(contradictions)} contradiction(s) detected")
        
        fraud_risk = reasoning_result.get("fraud_risk", 0)
        if fraud_risk >= 0.3:
            reasons.append(f"High fraud risk: {fraud_risk:.2f}")
        
        missing_evidence = reasoning_result.get("missing_evidence", [])
        if missing_evidence:
            reasons.append(f"Missing evidence: {', '.join(missing_evidence)}")
        
        return reasons
    
    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """Format agent results for summary generation."""
        formatted = []
        for agent_type, result in agent_results.items():
            if result:
                summary = result.get("summary", "Analysis completed")
                formatted.append(f"{agent_type.upper()}: {summary}")
        return "\n".join(formatted)
    
    async def _generate_summary_from_result(
        self,
        claim: Claim,
        result: Dict[str, Any]
    ) -> str:
        """Generate summary from orchestrator agent result."""
        try:
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return self._generate_template_summary_from_result(claim, result)
            
            import google.genai as genai
            client = genai.Client(api_key=api_key)
            model_name = os.getenv("AGENT_MODEL", "gemini-2.0-flash")
            
            # Map technical decision codes to user-friendly terms
            decision_map = {
                'AUTO_APPROVED': 'Approved',
                'APPROVED_WITH_REVIEW': 'Approved (pending review)',
                'NEEDS_REVIEW': 'Needs review',
                'NEEDS_MORE_DATA': 'Needs more information',
                'INSUFFICIENT_DATA': 'Insufficient information',
                'FRAUD_DETECTED': 'Rejected',
                'REJECTED': 'Rejected'
            }
            user_friendly_decision = decision_map.get(result.get('decision', 'UNKNOWN'), 'Under review')
            
            # Format requested data in user-friendly way
            requested_data = result.get('requested_data', [])
            if requested_data:
                data_needed = ', '.join([d.replace('_', ' ').title() for d in requested_data])
            else:
                data_needed = 'None'
            
            prompt = f"""Generate a clear, user-friendly summary for this insurance claim evaluation.

CRITICAL REQUIREMENTS:
1. Use ONLY the claim information provided below - do NOT reference other claims or claim IDs
2. Do NOT include technical details like:
   - Full claim IDs or UUIDs (like a9297b57-6f79-4bb9-9583-cd708361c2d0)
   - Wallet addresses or blockchain addresses (like 0x2fad2facda29bcfbe3b1ced92b289dfcc988353c)
   - Internal status codes (like INSUFFICIENT_DATA, EVALUATING, etc.)
   - Technical metrics (confidence percentages, thresholds like 95.00%)
   - Internal system details (tool calls, agent names, "No tools were called")

3. Write in plain language that a claimant or insurer can understand

Claim Information (USE THIS EXACT INFORMATION):
- Claim Amount: ${float(claim.claim_amount):,.2f}
- Status: {user_friendly_decision}
- Additional Information Needed: {data_needed}

Evaluation Details:
{result.get('reasoning', 'Evaluation completed.')}

Provide a clear, professional summary in plain language. Focus on:
- What was evaluated
- What decision was made
- What (if anything) is needed next
- Any important findings

Write as if explaining to a non-technical user. Do NOT mention claim IDs, wallet addresses, or technical system details."""
            
            aio_client = client.aio
            response = await aio_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            if hasattr(response, 'text'):
                summary = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                summary = response.candidates[0].content.parts[0].text
            else:
                summary = str(response)
            
            # Sanitize summary to remove technical details
            return self._sanitize_summary(summary, claim.id)
        except Exception as e:
            print(f"Error generating AI summary: {e}")
            template_summary = self._generate_template_summary_from_result(claim, result)
            return self._sanitize_summary(template_summary, claim.id)
    
    def _generate_template_summary_from_result(
        self,
        claim: Claim,
        result: Dict[str, Any]
    ) -> str:
        """Generate template-based summary from orchestrator agent result."""
        # Map technical decision codes to user-friendly terms
        decision_map = {
            'AUTO_APPROVED': 'Approved',
            'APPROVED_WITH_REVIEW': 'Approved (pending review)',
            'NEEDS_REVIEW': 'Needs review',
            'NEEDS_MORE_DATA': 'Needs more information',
            'INSUFFICIENT_DATA': 'Insufficient information',
            'FRAUD_DETECTED': 'Rejected',
            'REJECTED': 'Rejected'
        }
        decision = result.get('decision', 'UNKNOWN')
        user_friendly_decision = decision_map.get(decision, 'Under review')
        
        # Get user-friendly reasoning
        reasoning = result.get('reasoning', 'No reasoning provided')
        if not reasoning or reasoning == 'No reasoning provided':
            if decision == 'INSUFFICIENT_DATA':
                reasoning = 'The claim requires additional documentation to proceed with evaluation.'
            elif decision == 'NEEDS_MORE_DATA':
                reasoning = 'Additional information is needed to complete the evaluation.'
            elif decision == 'NEEDS_REVIEW':
                reasoning = 'This claim requires manual review by an insurer.'
            elif decision in ['AUTO_APPROVED', 'APPROVED_WITH_REVIEW']:
                reasoning = 'The claim has been approved based on the evaluation.'
            elif decision in ['FRAUD_DETECTED', 'REJECTED']:
                reasoning = 'The claim has been rejected based on the evaluation.'
        
        summary_parts = [
            f"**Claim Evaluation Summary**",
            "",
            f"**Status:** {user_friendly_decision}",
            "",
            f"**Evaluation:** {reasoning}",
            ""
        ]
        
        # Add requested data in user-friendly format
        requested_data = result.get('requested_data', [])
        if requested_data:
            data_needed = ', '.join([d.replace('_', ' ').title() for d in requested_data])
            summary_parts.append(f"**Additional Information Needed:** {data_needed}")
            summary_parts.append("")
        
        # Add human review note if needed
        if result.get('human_review_required'):
            summary_parts.append("**Note:** This claim requires manual review by an insurer.")
            if result.get('review_reasons'):
                reasons = result.get('review_reasons', [])
                if isinstance(reasons, list) and len(reasons) > 0:
                    summary_parts.append("")
                    summary_parts.append("**Review Reasons:**")
                    for reason in reasons:
                        summary_parts.append(f"- {reason}")
        
        summary = "\n".join(summary_parts)
        return self._sanitize_summary(summary, claim.id)


# Singleton instance
_adk_orchestrator: Optional[ADKOrchestrator] = None


def get_adk_orchestrator() -> ADKOrchestrator:
    """Get or create the ADK orchestrator singleton."""
    global _adk_orchestrator
    if _adk_orchestrator is None:
        _adk_orchestrator = ADKOrchestrator()
    return _adk_orchestrator
