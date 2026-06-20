from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta

from .models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules, LotSettlement,
    BidExclusion, LotStatus, BuyerType, DisputeType, DisputeStatus
)


def is_bid_valid(
    bid: Bid,
    lot: Lot,
    buyer: Buyer,
    all_bids: List[Bid],
    fee_rules: FeeRules
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if a bid is valid for settlement.
    
    Returns: (is_valid, reason, rule_name)
    """
    if bid.is_withdrawn:
        return False, "出价已被撤回", "RULE_WITHDRAWN_BID"
    
    if lot.status == LotStatus.WITHDRAWN:
        return False, "拍品已被管理员撤拍", "RULE_LOT_WITHDRAWN"
    
    if bid.timestamp < lot.withdrawal_time if lot.withdrawal_time else False:
        pass
    elif lot.withdrawal_time and bid.timestamp >= lot.withdrawal_time:
        return False, "出价时间晚于拍品撤拍时间", "RULE_LOT_WITHDRAWN"
    
    if bid.amount < lot.reserve_price:
        return False, f"出价 {bid.amount} 低于保留价 {lot.reserve_price}", "RULE_RESERVE_PRICE"
    
    if lot.restrict_individual_buyers and buyer.type == BuyerType.INDIVIDUAL:
        return False, "个人买家被限制参与此拍品", "RULE_INDIVIDUAL_RESTRICTED"
    
    if buyer.is_high_risk:
        required_deposit = lot.reserve_price * Decimal("0.2")
        if buyer.deposit_balance < required_deposit:
            return False, (
                f"高风险买家保证金不足: 需 {required_deposit}，"
                f"仅有 {buyer.deposit_balance}"
            ), "RULE_INSUFFICIENT_DEPOSIT"
    
    return True, None, None


def rank_bids(bids: List[Bid]) -> List[Bid]:
    """Rank bids by amount descending, then by timestamp ascending."""
    return sorted(bids, key=lambda b: (-b.amount, b.timestamp))


def process_lot_settlement(
    lot: Lot,
    bids: List[Bid],
    buyers: Dict[str, Buyer],
    sellers: Dict[str, Seller],
    disputes: List[Dispute],
    fee_rules: FeeRules
) -> LotSettlement:
    """Process settlement for a single lot."""
    from .fees import calculate_fees
    
    excluded_bids: List[BidExclusion] = []
    valid_bids: List[Bid] = []
    lot_disputes = [d for d in disputes if d.lot_id == lot.lot_id]
    audit_flags: List[str] = []
    explanation: List[str] = []

    if lot.status == LotStatus.WITHDRAWN:
        explanation.append(f"拍品 {lot.lot_id} 已被管理员撤拍，原因: {lot.withdrawal_reason}")
        audit_flags.append("LOT_WITHDRAWN")
        
        for bid in bids:
            buyer = buyers.get(bid.buyer_id)
            excluded_bids.append(BidExclusion(
                bid=bid,
                reason="拍品已撤拍",
                rule="RULE_LOT_WITHDRAWN"
            ))
        
        return LotSettlement(
            lot=lot,
            winning_bid=None,
            winning_buyer=None,
            excluded_bids=excluded_bids,
            is_sold=False,
            sale_price=None,
            fees={},
            buyer_total=None,
            seller_net=None,
            disputes=lot_disputes,
            audit_flags=audit_flags,
            explanation=explanation
        )

    for bid in bids:
        buyer = buyers.get(bid.buyer_id)
        if not buyer:
            excluded_bids.append(BidExclusion(
                bid=bid,
                reason=f"买家 {bid.buyer_id} 不存在",
                rule="RULE_INVALID_BUYER"
            ))
            continue
        
        is_valid, reason, rule = is_bid_valid(bid, lot, buyer, bids, fee_rules)
        if is_valid:
            valid_bids.append(bid)
        else:
            excluded_bids.append(BidExclusion(
                bid=bid,
                reason=reason or "未知原因",
                rule=rule or "RULE_UNKNOWN"
            ))

    if not valid_bids:
        explanation.append(f"拍品 {lot.lot_id} 无有效出价，流拍")
        return LotSettlement(
            lot=lot,
            winning_bid=None,
            winning_buyer=None,
            excluded_bids=excluded_bids,
            is_sold=False,
            sale_price=None,
            fees={},
            buyer_total=None,
            seller_net=None,
            disputes=lot_disputes,
            audit_flags=["UNSOLD_NO_VALID_BIDS"],
            explanation=explanation
        )

    ranked_bids = rank_bids(valid_bids)
    winning_bid = ranked_bids[0]
    winning_buyer = buyers[winning_bid.buyer_id]

    explanation.append(f"拍品 {lot.lot_id} 收到 {len(bids)} 个出价，其中 {len(valid_bids)} 个有效")
    explanation.append(f"有效出价按金额从高到低、时间从早到晚排序")
    
    for i, bid in enumerate(ranked_bids[:3]):
        buyer = buyers[bid.buyer_id]
        explanation.append(f"  第{i+1}名: {bid.amount} 元 (买家 {buyer.name}, 时间 {bid.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

    if len(ranked_bids) >= 2:
        second_bid = ranked_bids[1]
        if winning_bid.amount == second_bid.amount:
            explanation.append(
                f"前两名出价相同 ({winning_bid.amount})，"
                f"以更早出价 ({winning_bid.timestamp.strftime('%H:%M:%S')}) 优先"
            )

    fees = calculate_fees(lot, winning_bid, winning_buyer, sellers[lot.seller_id], fee_rules)
    
    buyer_total = winning_bid.amount
    for fee_name, fee_amount in fees.items():
        if fee_name.startswith("buyer_") or fee_name in [
            "inspection_fee", "packaging_fee", "cold_chain_fee", 
            "wooden_crate_fee", "logistics_fee", "tax"
        ]:
            buyer_total += fee_amount
    
    seller_net = winning_bid.amount
    for fee_name, fee_amount in fees.items():
        if fee_name.startswith("seller_") or fee_name == "platform_commission":
            seller_net -= fee_amount

    explanation.append(f"最终成交价: {winning_bid.amount} 元")
    explanation.append(f"买家: {winning_buyer.name}")
    explanation.append(f"费用明细:")
    for fee_name, fee_amount in fees.items():
        explanation.append(f"  {fee_name}: {fee_amount} 元")
    explanation.append(f"买家应付总计: {buyer_total} 元")
    explanation.append(f"卖家净得: {seller_net} 元")

    for dispute in lot_disputes:
        if dispute.status == DisputeStatus.OPEN:
            audit_flags.append(f"DISPUTE_OPEN_{dispute.type.value}")
        elif dispute.status == DisputeStatus.NEEDS_REVIEW:
            audit_flags.append(f"DISPUTE_REVIEW_{dispute.type.value}")

    return LotSettlement(
        lot=lot,
        winning_bid=winning_bid,
        winning_buyer=winning_buyer,
        excluded_bids=excluded_bids,
        is_sold=True,
        sale_price=winning_bid.amount,
        fees=fees,
        buyer_total=buyer_total,
        seller_net=seller_net,
        disputes=lot_disputes,
        audit_flags=audit_flags,
        explanation=explanation
    )


def process_batch_settlement(
    batch_id: str,
    lots: List[Lot],
    bids: List[Bid],
    buyers: List[Buyer],
    sellers: List[Seller],
    disputes: List[Dispute],
    fee_rules: FeeRules
) -> Tuple[List[LotSettlement], List[Dict[str, Any]]]:
    """Process settlement for a batch of lots."""
    buyer_map = {b.buyer_id: b for b in buyers}
    seller_map = {s.seller_id: s for s in sellers}
    bids_by_lot: Dict[str, List[Bid]] = {}
    
    for bid in bids:
        bids_by_lot.setdefault(bid.lot_id, []).append(bid)
    
    settlements: List[LotSettlement] = []
    audit_findings: List[Dict[str, Any]] = []

    for lot in lots:
        lot_bids = bids_by_lot.get(lot.lot_id, [])
        settlement = process_lot_settlement(
            lot, lot_bids, buyer_map, seller_map, disputes, fee_rules
        )
        settlements.append(settlement)

    from .audit import run_audit
    audit_findings = run_audit(lots, bids, buyers, sellers, disputes, settlements, fee_rules)

    return settlements, audit_findings
