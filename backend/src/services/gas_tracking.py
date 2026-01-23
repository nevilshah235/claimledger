"""
Gas tracking for settlement transactions.

Fetches gas used and cost from Arc RPC and caches in SettlementGas.
"""

import logging
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import SettlementGas
from .arc_rpc import get_gas_payment

logger = logging.getLogger(__name__)


def record_settlement_gas(claim_id: str, tx_hash: str, db: Session) -> None:
    """
    Fetch gas payment for a settlement tx from Arc RPC and store in SettlementGas.

    Idempotent: if a SettlementGas record already exists for this tx_hash, no-op.
    If the tx is pending or RPC fails, no record is created (caller can retry later).
    """
    if not claim_id or not tx_hash:
        return
    existing = db.query(SettlementGas).filter(SettlementGas.tx_hash == tx_hash).first()
    if existing:
        return
    data = get_gas_payment(tx_hash)
    if not data:
        return
    try:
        sg = SettlementGas(
            claim_id=claim_id,
            tx_hash=tx_hash,
            gas_used=data["gas_used"],
            gas_price_wei=data["gas_price_wei"],
            cost_wei=data["cost_wei"],
            cost_arc=Decimal(str(data["cost_arc"])),
        )
        db.add(sg)
        db.commit()
    except Exception as e:
        logger.warning("Could not save SettlementGas for %s: %s", tx_hash[:18], e)
        db.rollback()
