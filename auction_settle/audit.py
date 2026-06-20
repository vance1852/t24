from decimal import Decimal
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules, LotSettlement,
    LotStatus, DisputeType, DisputeStatus, BuyerType
)


def run_audit(
    lots: List[Lot],
    bids: List[Bid],
    buyers: List[Buyer],
    sellers: List[Seller],
    disputes: List[Dispute],
    settlements: List[LotSettlement],
    fee_rules: FeeRules
) -> List[Dict[str, Any]]:
    """Run comprehensive audit on auction data."""
    findings: List[Dict[str, Any]] = []

    findings.extend(check_suspicious_bidding(bids, buyers))
    findings.extend(check_price_anomalies(settlements))
    findings.extend(check_insufficient_deposit(bids, lots, buyers, settlements, fee_rules))
    findings.extend(check_lot_withdrawal_bids(lots, bids))
    findings.extend(check_cold_chain_fees(settlements))
    findings.extend(check_duplicate_serials(lots))
    findings.extend(check_withdrawn_bids_impact(bids, settlements))
    findings.extend(check_dispute_resolutions(disputes, settlements))

    return findings


def check_suspicious_bidding(bids: List[Bid], buyers: List[Buyer]) -> List[Dict[str, Any]]:
    """Check for suspicious bidding patterns like rapid consecutive bids."""
    findings: List[Dict[str, Any]] = []
    buyer_map = {b.buyer_id: b for b in buyers}
    bids_by_buyer_lot: Dict[Tuple[str, str], List[Bid]] = defaultdict(list)

    for bid in bids:
        if not bid.is_withdrawn:
            bids_by_buyer_lot[(bid.buyer_id, bid.lot_id)].append(bid)

    for (buyer_id, lot_id), buyer_bids in bids_by_buyer_lot.items():
        if len(buyer_bids) < 2:
            continue

        sorted_bids = sorted(buyer_bids, key=lambda b: b.timestamp)
        for i in range(1, len(sorted_bids)):
            time_diff = sorted_bids[i].timestamp - sorted_bids[i-1].timestamp
            if time_diff <= timedelta(minutes=2):
                buyer = buyer_map.get(buyer_id)
                findings.append({
                    "type": "SUSPICIOUS_BIDDING",
                    "severity": "medium",
                    "lot_id": lot_id,
                    "buyer_id": buyer_id,
                    "buyer_name": buyer.name if buyer else "Unknown",
                    "description": (
                        f"买家在短时间内({time_diff.total_seconds():.0f}秒)连续出价: "
                        f"{sorted_bids[i-1].amount} -> {sorted_bids[i].amount}"
                    ),
                    "recommendation": "需要人工复核是否存在恶意抬价行为",
                    "related_bids": [b.bid_id for b in sorted_bids[i-1:i+1]],
                })

    return findings


def check_price_anomalies(settlements: List[LotSettlement]) -> List[Dict[str, Any]]:
    """Check for price anomalies where sale price deviates significantly from estimated value."""
    findings: List[Dict[str, Any]] = []

    for s in settlements:
        if not s.is_sold or not s.sale_price or not s.lot.estimated_value:
            continue

        deviation = (s.sale_price - s.lot.estimated_value) / s.lot.estimated_value * 100

        if deviation >= 100:
            findings.append({
                "type": "PRICE_ANOMALY_HIGH",
                "severity": "high",
                "lot_id": s.lot.lot_id,
                "lot_name": s.lot.name,
                "sale_price": str(s.sale_price),
                "estimated_value": str(s.lot.estimated_value),
                "deviation_percent": f"{deviation:.1f}%",
                "description": f"成交价比估值高出{deviation:.1f}%，可能存在异常出价",
                "recommendation": "需要人工复核出价真实性",
                "winning_bid_id": s.winning_bid.bid_id if s.winning_bid else None,
                "winning_buyer_id": s.winning_buyer.buyer_id if s.winning_buyer else None,
            })
        elif deviation <= -50:
            findings.append({
                "type": "PRICE_ANOMALY_LOW",
                "severity": "medium",
                "lot_id": s.lot.lot_id,
                "lot_name": s.lot.name,
                "sale_price": str(s.sale_price),
                "estimated_value": str(s.lot.estimated_value),
                "deviation_percent": f"{deviation:.1f}%",
                "description": f"成交价比估值低出{abs(deviation):.1f}%，需要关注",
                "recommendation": "建议复核是否存在漏拍或低价处置情况",
                "winning_bid_id": s.winning_bid.bid_id if s.winning_bid else None,
                "winning_buyer_id": s.winning_buyer.buyer_id if s.winning_buyer else None,
            })

    return findings


def check_insufficient_deposit(
    bids: List[Bid],
    lots: List[Lot],
    buyers: List[Buyer],
    settlements: List[LotSettlement],
    fee_rules: FeeRules
) -> List[Dict[str, Any]]:
    """Check for high-risk buyers with insufficient deposit winning bids."""
    findings: List[Dict[str, Any]] = []
    buyer_map = {b.buyer_id: b for b in buyers}
    lot_map = {l.lot_id: l for l in lots}

    for s in settlements:
        if not s.is_sold or not s.winning_buyer or not s.winning_bid:
            continue

        buyer = s.winning_buyer
        lot = s.lot

        if buyer.is_high_risk:
            required_deposit = lot.reserve_price * Decimal("0.2")
            if buyer.deposit_balance < required_deposit:
                findings.append({
                    "type": "INSUFFICIENT_DEPOSIT",
                    "severity": "high",
                    "lot_id": lot.lot_id,
                    "lot_name": lot.name,
                    "buyer_id": buyer.buyer_id,
                    "buyer_name": buyer.name,
                    "required_deposit": str(required_deposit),
                    "actual_deposit": str(buyer.deposit_balance),
                    "description": (
                        f"高风险买家保证金不足: 需{required_deposit}元，"
                        f"仅有{buyer.deposit_balance}元，但仍赢得了拍品"
                    ),
                    "recommendation": "应取消成交资格或要求补足保证金",
                    "winning_bid_id": s.winning_bid.bid_id,
                })

    return findings


def check_lot_withdrawal_bids(lots: List[Lot], bids: List[Bid]) -> List[Dict[str, Any]]:
    """Check for bids placed after lot withdrawal."""
    findings: List[Dict[str, Any]] = []
    lot_map = {l.lot_id: l for l in lots}

    for bid in bids:
        lot = lot_map.get(bid.lot_id)
        if not lot or lot.status != LotStatus.WITHDRAWN:
            continue

        if lot.withdrawal_time and bid.timestamp >= lot.withdrawal_time:
            findings.append({
                "type": "BID_AFTER_WITHDRAWAL",
                "severity": "medium",
                "lot_id": lot.lot_id,
                "lot_name": lot.name,
                "bid_id": bid.bid_id,
                "buyer_id": bid.buyer_id,
                "bid_amount": str(bid.amount),
                "bid_time": bid.timestamp.isoformat(),
                "withdrawal_time": lot.withdrawal_time.isoformat(),
                "description": (
                    f"出价时间({bid.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) "
                    f"晚于拍品撤拍时间({lot.withdrawal_time.strftime('%Y-%m-%d %H:%M:%S')})"
                ),
                "recommendation": "该出价应自动作废，不计入结算",
            })

    return findings


def check_cold_chain_fees(settlements: List[LotSettlement]) -> List[Dict[str, Any]]:
    """Check that cold chain fees are applied for cold chain required lots."""
    findings: List[Dict[str, Any]] = []

    for s in settlements:
        if not s.is_sold:
            continue

        if s.lot.requires_cold_chain and "cold_chain_fee" not in s.fees:
            findings.append({
                "type": "COLD_CHAIN_FEE_MISSING",
                "severity": "high",
                "lot_id": s.lot.lot_id,
                "lot_name": s.lot.name,
                "description": "需要冷链运输的拍品未收取冷链费",
                "recommendation": "应补收冷链费或确认是否有特殊豁免",
            })

    return findings


def check_duplicate_serials(lots: List[Lot]) -> List[Dict[str, Any]]:
    """Check for duplicate equipment serial numbers."""
    findings: List[Dict[str, Any]] = []
    serials: Dict[str, List[Lot]] = defaultdict(list)

    for lot in lots:
        if lot.serial_number:
            serials[lot.serial_number].append(lot)

    for serial, serial_lots in serials.items():
        if len(serial_lots) > 1:
            findings.append({
                "type": "DUPLICATE_SERIAL",
                "severity": "high",
                "serial_number": serial,
                "lot_ids": [l.lot_id for l in serial_lots],
                "lot_names": [l.name for l in serial_lots],
                "description": (
                    f"设备序列号 {serial} 出现在 {len(serial_lots)} 个拍品中: "
                    f"{', '.join(l.lot_id for l in serial_lots)}"
                ),
                "recommendation": "需要人工确认是否为同一设备重复上拍",
            })

    return findings


def check_withdrawn_bids_impact(bids: List[Bid], settlements: List[LotSettlement]) -> List[Dict[str, Any]]:
    """Check that withdrawn bids don't affect settlement outcomes."""
    findings: List[Dict[str, Any]] = []
    withdrawn_bids = [b for b in bids if b.is_withdrawn]

    for bid in withdrawn_bids:
        findings.append({
            "type": "WITHDRAWN_BID",
            "severity": "low",
            "lot_id": bid.lot_id,
            "bid_id": bid.bid_id,
            "buyer_id": bid.buyer_id,
            "amount": str(bid.amount),
            "withdrawal_reason": bid.withdrawal_reason,
            "description": f"出价 {bid.bid_id} 已被撤回，已排除在结算外",
            "recommendation": "已自动处理，无需人工干预",
        })

    return findings


def check_dispute_resolutions(
    disputes: List[Dispute],
    settlements: List[LotSettlement]
) -> List[Dict[str, Any]]:
    """Evaluate disputes and suggest resolutions."""
    findings: List[Dict[str, Any]] = []
    settlement_map = {s.lot.lot_id: s for s in settlements}

    for dispute in disputes:
        if dispute.status == DisputeStatus.RESOLVED:
            continue

        recommendation = evaluate_dispute(dispute, settlement_map.get(dispute.lot_id))
        status_suggestion = suggest_dispute_status(dispute, recommendation)

        findings.append({
            "type": f"DISPUTE_{dispute.type.value}",
            "severity": get_dispute_severity(dispute.type),
            "dispute_id": dispute.dispute_id,
            "lot_id": dispute.lot_id,
            "bid_id": dispute.bid_id,
            "buyer_id": dispute.buyer_id,
            "seller_id": dispute.seller_id,
            "description": dispute.description,
            "current_status": dispute.status.value,
            "suggested_status": status_suggestion.value,
            "recommendation": recommendation,
        })

    return findings


def evaluate_dispute(dispute: Dispute, settlement: LotSettlement) -> str:
    """Evaluate a dispute and provide resolution recommendation."""
    if dispute.type == DisputeType.WITHDRAWN_BID:
        return "撤回的出价已自动排除在结算外，不影响最终成交结果，可自动驳回争议"
    elif dispute.type == DisputeType.RESERVE_PRICE:
        if settlement and not settlement.is_sold:
            return "低于保留价的出价已被正确排除，拍品流拍处理正确"
        return "需要人工核实出价是否确实高于保留价"
    elif dispute.type == DisputeType.INSUFFICIENT_DEPOSIT:
        return "高风险买家保证金不足的出价应被排除，需核实最终成交人资格"
    elif dispute.type == DisputeType.SUSPICIOUS_BIDDING:
        return "需要人工核查出价历史，判断是否存在恶意抬价或串标行为"
    elif dispute.type == DisputeType.COLD_CHAIN_MISSING:
        return "需要核实冷链费用是否应收取，如漏收需补收或办理豁免"
    elif dispute.type == DisputeType.DUPLICATE_SERIAL:
        return "需要人工确认是否为同一设备重复上拍，必要时撤销其中一个拍品"
    elif dispute.type == DisputeType.PRICE_ANOMALY:
        return "需要人工复核出价真实性，确认是否存在操作失误或异常出价"
    elif dispute.type == DisputeType.LOT_WITHDRAWN:
        return "已撤拍拍品的所有出价均已作废，需通知相关买家"
    else:
        return "需要人工复核争议内容后作出处理"


def suggest_dispute_status(dispute: Dispute, recommendation: str) -> DisputeStatus:
    """Suggest a status for the dispute based on type and recommendation."""
    auto_dismiss_types = [DisputeType.WITHDRAWN_BID, DisputeType.RESERVE_PRICE]
    
    if dispute.type in auto_dismiss_types and "可自动驳回" in recommendation:
        return DisputeStatus.AUTO_DISMISSED
    elif "建议退款" in recommendation or "应取消" in recommendation:
        return DisputeStatus.REFUND_SUGGESTED
    elif dispute.status == DisputeStatus.OPEN:
        return DisputeStatus.NEEDS_REVIEW
    return dispute.status


def get_dispute_severity(dispute_type: DisputeType) -> str:
    """Get severity level for a dispute type."""
    high_severity = [
        DisputeType.INSUFFICIENT_DEPOSIT,
        DisputeType.DUPLICATE_SERIAL,
        DisputeType.COLD_CHAIN_MISSING,
    ]
    medium_severity = [
        DisputeType.PRICE_ANOMALY,
        DisputeType.SUSPICIOUS_BIDDING,
        DisputeType.LOT_WITHDRAWN,
    ]
    
    if dispute_type in high_severity:
        return "high"
    elif dispute_type in medium_severity:
        return "medium"
    return "low"
