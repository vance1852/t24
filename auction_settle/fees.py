from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

from .models import Lot, Bid, Buyer, Seller, FeeRules


def calculate_fees(
    lot: Lot,
    winning_bid: Bid,
    buyer: Buyer,
    seller: Seller,
    fee_rules: FeeRules
) -> Dict[str, Decimal]:
    """Calculate all fees for a lot settlement using Decimal precision."""
    sale_price = winning_bid.amount
    fees: Dict[str, Decimal] = {}

    platform_commission = sale_price * fee_rules.platform_commission_rate
    fees["platform_commission"] = _round(platform_commission)

    inspection_fee = sale_price * fee_rules.inspection_fee_rate
    fees["inspection_fee"] = _round(inspection_fee)

    packaging_fee = fee_rules.packaging_fee
    fees["packaging_fee"] = _round(packaging_fee)

    if lot.requires_cold_chain:
        cold_chain_fee = fee_rules.cold_chain_fee
        fees["cold_chain_fee"] = _round(cold_chain_fee)

    if lot.requires_wooden_crate:
        wooden_crate_fee = fee_rules.wooden_crate_fee
        fees["wooden_crate_fee"] = _round(wooden_crate_fee)

    if buyer.province != seller.province:
        logistics_fee = fee_rules.inter_provincial_logistics_fee
    else:
        logistics_fee = fee_rules.intra_provincial_logistics_fee
    fees["logistics_fee"] = _round(logistics_fee)

    if lot.allows_split_shipment:
        split_shipment_surcharge = fee_rules.split_shipment_surcharge
        fees["split_shipment_surcharge"] = _round(split_shipment_surcharge)

    taxable_amount = sale_price
    for fee_name in [
        "inspection_fee", "packaging_fee", "cold_chain_fee",
        "wooden_crate_fee", "logistics_fee", "split_shipment_surcharge"
    ]:
        if fee_name in fees:
            taxable_amount += fees[fee_name]
    
    tax = taxable_amount * fee_rules.tax_rate
    fees["tax"] = _round(tax)

    return fees


def calculate_buyer_bill(
    buyer: Buyer,
    settlements: list,
    fee_rules: FeeRules
) -> dict:
    """Calculate the total bill for a buyer."""
    from .models import BuyerBill
    
    buyer_settlements = [s for s in settlements if s.winning_buyer and s.winning_buyer.buyer_id == buyer.buyer_id]
    
    total_purchase = Decimal("0")
    for s in buyer_settlements:
        total_purchase += (s.sale_price or Decimal("0"))
    
    total_fees = Decimal("0")
    for s in buyer_settlements:
        for fee_name, fee_amount in s.fees.items():
            if fee_name.startswith("buyer_") or fee_name in [
                "inspection_fee", "packaging_fee", "cold_chain_fee",
                "wooden_crate_fee", "logistics_fee", "split_shipment_surcharge", "tax"
            ]:
                total_fees += fee_amount

    deposit_applied = min(buyer.deposit_balance, total_purchase + total_fees)
    penalties = Decimal("0")
    amount_due = total_purchase + total_fees - deposit_applied + penalties

    return BuyerBill(
        buyer=buyer,
        settlements=buyer_settlements,
        total_purchase=_round(total_purchase),
        total_fees=_round(total_fees),
        deposit_applied=_round(deposit_applied),
        penalties=_round(penalties),
        amount_due=_round(amount_due)
    )


def calculate_seller_statement(
    seller: Seller,
    settlements: list,
    fee_rules: FeeRules
) -> dict:
    """Calculate the settlement statement for a seller."""
    from .models import SellerStatement
    
    seller_settlements = [s for s in settlements if s.lot.seller_id == seller.seller_id]
    
    total_sales = Decimal("0")
    total_fees = Decimal("0")
    penalties = Decimal("0")
    sold_count = 0
    withdrawn_count = 0
    
    from .models import LotStatus
    for s in seller_settlements:
        if s.lot.status == LotStatus.WITHDRAWN:
            penalties += fee_rules.seller_withdrawal_penalty
            withdrawn_count += 1
        elif s.is_sold:
            total_sales += (s.sale_price or Decimal("0"))
            sold_count += 1
            for fee_name, fee_amount in s.fees.items():
                if fee_name.startswith("seller_") or fee_name == "platform_commission":
                    total_fees += fee_amount

    net_amount = total_sales - total_fees - penalties

    return SellerStatement(
        seller=seller,
        settlements=seller_settlements,
        total_sales=_round(total_sales),
        total_fees=_round(total_fees),
        penalties=_round(penalties),
        net_amount=_round(net_amount),
        sold_count=sold_count,
        withdrawn_count=withdrawn_count
    )


def _round(value: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
