from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class LotStatus(str, Enum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    SOLD = "sold"
    UNSOLD = "unsold"


class InspectionGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DisputeStatus(str, Enum):
    OPEN = "open"
    AUTO_DISMISSED = "auto_dismissed"
    NEEDS_REVIEW = "needs_review"
    REFUND_SUGGESTED = "refund_suggested"
    RESOLVED = "resolved"


class DisputeType(str, Enum):
    WITHDRAWN_BID = "withdrawn_bid"
    RESERVE_PRICE = "reserve_price"
    INSUFFICIENT_DEPOSIT = "insufficient_deposit"
    SUSPICIOUS_BIDDING = "suspicious_bidding"
    COLD_CHAIN_MISSING = "cold_chain_missing"
    DUPLICATE_SERIAL = "duplicate_serial"
    PRICE_ANOMALY = "price_anomaly"
    LOT_WITHDRAWN = "lot_withdrawn"
    OTHER = "other"


class BuyerType(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    INSTITUTION = "institution"


@dataclass
class FeeRules:
    platform_commission_rate: Decimal = Decimal("0.05")
    inspection_fee_rate: Decimal = Decimal("0.02")
    packaging_fee: Decimal = Decimal("50.00")
    cold_chain_fee: Decimal = Decimal("200.00")
    wooden_crate_fee: Decimal = Decimal("150.00")
    inter_provincial_logistics_fee: Decimal = Decimal("300.00")
    intra_provincial_logistics_fee: Decimal = Decimal("100.00")
    default_buyer_penalty_rate: Decimal = Decimal("0.50")
    seller_withdrawal_penalty: Decimal = Decimal("200.00")
    split_shipment_surcharge: Decimal = Decimal("50.00")
    tax_rate: Decimal = Decimal("0.13")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform_commission_rate": str(self.platform_commission_rate),
            "inspection_fee_rate": str(self.inspection_fee_rate),
            "packaging_fee": str(self.packaging_fee),
            "cold_chain_fee": str(self.cold_chain_fee),
            "wooden_crate_fee": str(self.wooden_crate_fee),
            "inter_provincial_logistics_fee": str(self.inter_provincial_logistics_fee),
            "intra_provincial_logistics_fee": str(self.intra_provincial_logistics_fee),
            "default_buyer_penalty_rate": str(self.default_buyer_penalty_rate),
            "seller_withdrawal_penalty": str(self.seller_withdrawal_penalty),
            "split_shipment_surcharge": str(self.split_shipment_surcharge),
            "tax_rate": str(self.tax_rate),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeeRules":
        return cls(
            platform_commission_rate=Decimal(data.get("platform_commission_rate", "0.05")),
            inspection_fee_rate=Decimal(data.get("inspection_fee_rate", "0.02")),
            packaging_fee=Decimal(data.get("packaging_fee", "50.00")),
            cold_chain_fee=Decimal(data.get("cold_chain_fee", "200.00")),
            wooden_crate_fee=Decimal(data.get("wooden_crate_fee", "150.00")),
            inter_provincial_logistics_fee=Decimal(data.get("inter_provincial_logistics_fee", "300.00")),
            intra_provincial_logistics_fee=Decimal(data.get("intra_provincial_logistics_fee", "100.00")),
            default_buyer_penalty_rate=Decimal(data.get("default_buyer_penalty_rate", "0.50")),
            seller_withdrawal_penalty=Decimal(data.get("seller_withdrawal_penalty", "200.00")),
            split_shipment_surcharge=Decimal(data.get("split_shipment_surcharge", "50.00")),
            tax_rate=Decimal(data.get("tax_rate", "0.13")),
        )


@dataclass
class Buyer:
    buyer_id: str
    name: str
    email: str
    type: BuyerType
    province: str
    deposit_balance: Decimal
    is_high_risk: bool = False
    phone: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer_id,
            "name": self.name,
            "email": self.email,
            "type": self.type.value,
            "province": self.province,
            "deposit_balance": str(self.deposit_balance),
            "is_high_risk": self.is_high_risk,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Buyer":
        return cls(
            buyer_id=data["buyer_id"],
            name=data["name"],
            email=data["email"],
            type=BuyerType(data["type"]),
            province=data["province"],
            deposit_balance=Decimal(data["deposit_balance"]),
            is_high_risk=data.get("is_high_risk", False),
            phone=data.get("phone"),
        )


@dataclass
class Seller:
    seller_id: str
    name: str
    email: str
    province: str
    phone: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "email": self.email,
            "province": self.province,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Seller":
        return cls(
            seller_id=data["seller_id"],
            name=data["name"],
            email=data["email"],
            province=data["province"],
            phone=data.get("phone"),
        )


@dataclass
class Lot:
    lot_id: str
    name: str
    description: str
    category: str
    serial_number: Optional[str]
    inspection_grade: InspectionGrade
    estimated_value: Decimal
    reserve_price: Decimal
    requires_cold_chain: bool
    requires_wooden_crate: bool
    restrict_individual_buyers: bool
    allows_split_shipment: bool
    seller_id: str
    status: LotStatus = LotStatus.ACTIVE
    withdrawal_reason: Optional[str] = None
    withdrawal_time: Optional[datetime] = None
    location: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "serial_number": self.serial_number,
            "inspection_grade": self.inspection_grade.value,
            "estimated_value": str(self.estimated_value),
            "reserve_price": str(self.reserve_price),
            "requires_cold_chain": self.requires_cold_chain,
            "requires_wooden_crate": self.requires_wooden_crate,
            "restrict_individual_buyers": self.restrict_individual_buyers,
            "allows_split_shipment": self.allows_split_shipment,
            "seller_id": self.seller_id,
            "status": self.status.value,
            "withdrawal_reason": self.withdrawal_reason,
            "withdrawal_time": self.withdrawal_time.isoformat() if self.withdrawal_time else None,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lot":
        return cls(
            lot_id=data["lot_id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            serial_number=data.get("serial_number"),
            inspection_grade=InspectionGrade(data["inspection_grade"]),
            estimated_value=Decimal(data["estimated_value"]),
            reserve_price=Decimal(data["reserve_price"]),
            requires_cold_chain=data.get("requires_cold_chain", False),
            requires_wooden_crate=data.get("requires_wooden_crate", False),
            restrict_individual_buyers=data.get("restrict_individual_buyers", False),
            allows_split_shipment=data.get("allows_split_shipment", False),
            seller_id=data["seller_id"],
            status=LotStatus(data.get("status", "active")),
            withdrawal_reason=data.get("withdrawal_reason"),
            withdrawal_time=datetime.fromisoformat(data["withdrawal_time"]) if data.get("withdrawal_time") else None,
            location=data.get("location"),
        )


@dataclass
class Bid:
    bid_id: str
    lot_id: str
    buyer_id: str
    amount: Decimal
    timestamp: datetime
    is_withdrawn: bool = False
    withdrawal_reason: Optional[str] = None
    withdrawal_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bid_id": self.bid_id,
            "lot_id": self.lot_id,
            "buyer_id": self.buyer_id,
            "amount": str(self.amount),
            "timestamp": self.timestamp.isoformat(),
            "is_withdrawn": self.is_withdrawn,
            "withdrawal_reason": self.withdrawal_reason,
            "withdrawal_time": self.withdrawal_time.isoformat() if self.withdrawal_time else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bid":
        return cls(
            bid_id=data["bid_id"],
            lot_id=data["lot_id"],
            buyer_id=data["buyer_id"],
            amount=Decimal(data["amount"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            is_withdrawn=data.get("is_withdrawn", False),
            withdrawal_reason=data.get("withdrawal_reason"),
            withdrawal_time=datetime.fromisoformat(data["withdrawal_time"]) if data.get("withdrawal_time") else None,
        )


@dataclass
class Dispute:
    dispute_id: str
    lot_id: str
    bid_id: Optional[str]
    type: DisputeType
    description: str
    status: DisputeStatus = DisputeStatus.OPEN
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dispute_id": self.dispute_id,
            "lot_id": self.lot_id,
            "bid_id": self.bid_id,
            "type": self.type.value,
            "description": self.description,
            "status": self.status.value,
            "buyer_id": self.buyer_id,
            "seller_id": self.seller_id,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dispute":
        return cls(
            dispute_id=data["dispute_id"],
            lot_id=data["lot_id"],
            bid_id=data.get("bid_id"),
            type=DisputeType(data["type"]),
            description=data["description"],
            status=DisputeStatus(data.get("status", "open")),
            buyer_id=data.get("buyer_id"),
            seller_id=data.get("seller_id"),
            resolution_notes=data.get("resolution_notes"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
        )


@dataclass
class BidExclusion:
    bid: Bid
    reason: str
    rule: str


@dataclass
class LotSettlement:
    lot: Lot
    winning_bid: Optional[Bid]
    winning_buyer: Optional[Buyer]
    excluded_bids: List[BidExclusion]
    is_sold: bool
    sale_price: Optional[Decimal]
    fees: Dict[str, Decimal]
    buyer_total: Optional[Decimal]
    seller_net: Optional[Decimal]
    disputes: List[Dispute]
    audit_flags: List[str]
    explanation: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lot_id": self.lot.lot_id,
            "lot_name": self.lot.name,
            "is_sold": self.is_sold,
            "sale_price": str(self.sale_price) if self.sale_price else None,
            "winning_buyer_id": self.winning_buyer.buyer_id if self.winning_buyer else None,
            "winning_buyer_name": self.winning_buyer.name if self.winning_buyer else None,
            "winning_bid_id": self.winning_bid.bid_id if self.winning_bid else None,
            "fees": {k: str(v) for k, v in self.fees.items()},
            "buyer_total": str(self.buyer_total) if self.buyer_total else None,
            "seller_net": str(self.seller_net) if self.seller_net else None,
            "excluded_bids": [
                {
                    "bid_id": be.bid.bid_id,
                    "buyer_id": be.bid.buyer_id,
                    "amount": str(be.bid.amount),
                    "reason": be.reason,
                    "rule": be.rule,
                }
                for be in self.excluded_bids
            ],
            "disputes": [d.to_dict() for d in self.disputes],
            "audit_flags": self.audit_flags,
            "explanation": self.explanation,
        }


@dataclass
class BuyerBill:
    buyer: Buyer
    settlements: List[LotSettlement]
    total_purchase: Decimal
    total_fees: Decimal
    deposit_applied: Decimal
    penalties: Decimal
    amount_due: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer.buyer_id,
            "buyer_name": self.buyer.name,
            "total_purchase": str(self.total_purchase),
            "total_fees": str(self.total_fees),
            "deposit_applied": str(self.deposit_applied),
            "penalties": str(self.penalties),
            "amount_due": str(self.amount_due),
            "items": [
                {
                    "lot_id": s.lot.lot_id,
                    "lot_name": s.lot.name,
                    "sale_price": str(s.sale_price),
                    "fees": {k: str(v) for k, v in s.fees.items()},
                }
                for s in self.settlements
            ],
        }


@dataclass
class SellerStatement:
    seller: Seller
    settlements: List[LotSettlement]
    total_sales: Decimal
    total_fees: Decimal
    penalties: Decimal
    net_amount: Decimal
    sold_count: int = 0
    withdrawn_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seller_id": self.seller.seller_id,
            "seller_name": self.seller.name,
            "total_sales": str(self.total_sales),
            "total_fees": str(self.total_fees),
            "penalties": str(self.penalties),
            "net_amount": str(self.net_amount),
            "items": [
                {
                    "lot_id": s.lot.lot_id,
                    "lot_name": s.lot.name,
                    "sale_price": str(s.sale_price) if s.sale_price else None,
                    "fees": {k: str(v) for k, v in s.fees.items()},
                    "is_sold": s.is_sold,
                }
                for s in self.settlements
            ],
        }


@dataclass
class BatchResult:
    batch_id: str
    settlements: List[LotSettlement]
    buyer_bills: List[BuyerBill]
    seller_statements: List[SellerStatement]
    total_sales: Decimal
    total_fees: Decimal
    total_penalties: Decimal
    audit_findings: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_sales": str(self.total_sales),
            "total_fees": str(self.total_fees),
            "total_penalties": str(self.total_penalties),
            "settlements": [s.to_dict() for s in self.settlements],
            "buyer_bills": [b.to_dict() for b in self.buyer_bills],
            "seller_statements": [s.to_dict() for s in self.seller_statements],
            "audit_findings": self.audit_findings,
        }
