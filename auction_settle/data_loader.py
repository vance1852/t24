import json
import csv
import os
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from .models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules,
    LotStatus, InspectionGrade, DisputeType, DisputeStatus, BuyerType
)


def get_default_data_dir() -> str:
    """Get the default data directory path."""
    return os.path.join(os.path.dirname(__file__), "sample_data", "data")


def get_user_data_dir() -> str:
    """Get the user's working data directory."""
    return os.path.join(os.getcwd(), "auction_data")


def ensure_data_dir(data_dir: Optional[str] = None) -> str:
    """Ensure the data directory exists and return its path."""
    if data_dir is None:
        data_dir = get_user_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def load_json_file(file_path: str) -> Any:
    """Load and parse a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path: str, data: Any) -> None:
    """Save data to a JSON file with pretty printing."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_fee_rules(data_dir: Optional[str] = None) -> FeeRules:
    """Load fee rules from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "fee_rules.json")
    data = load_json_file(file_path)
    return FeeRules.from_dict(data)


def load_lots(data_dir: Optional[str] = None) -> List[Lot]:
    """Load lots from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "lots.json")
    data = load_json_file(file_path)
    return [Lot.from_dict(item) for item in data]


def load_bids(data_dir: Optional[str] = None) -> List[Bid]:
    """Load bids from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "bids.json")
    data = load_json_file(file_path)
    return [Bid.from_dict(item) for item in data]


def load_buyers(data_dir: Optional[str] = None) -> List[Buyer]:
    """Load buyers from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "buyers.json")
    data = load_json_file(file_path)
    return [Buyer.from_dict(item) for item in data]


def load_sellers(data_dir: Optional[str] = None) -> List[Seller]:
    """Load sellers from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "sellers.json")
    data = load_json_file(file_path)
    return [Seller.from_dict(item) for item in data]


def load_disputes(data_dir: Optional[str] = None) -> List[Dispute]:
    """Load disputes from JSON file."""
    data_dir = data_dir or get_default_data_dir()
    file_path = os.path.join(data_dir, "disputes.json")
    data = load_json_file(file_path)
    return [Dispute.from_dict(item) for item in data]


def load_all_data(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Load all auction data from the specified directory."""
    return {
        "fee_rules": load_fee_rules(data_dir),
        "lots": load_lots(data_dir),
        "bids": load_bids(data_dir),
        "buyers": load_buyers(data_dir),
        "sellers": load_sellers(data_dir),
        "disputes": load_disputes(data_dir),
    }


def save_lots(lots: List[Lot], data_dir: str) -> None:
    """Save lots to JSON file."""
    file_path = os.path.join(data_dir, "lots.json")
    save_json_file(file_path, [l.to_dict() for l in lots])


def save_bids(bids: List[Bid], data_dir: str) -> None:
    """Save bids to JSON file."""
    file_path = os.path.join(data_dir, "bids.json")
    save_json_file(file_path, [b.to_dict() for b in bids])


def save_buyers(buyers: List[Buyer], data_dir: str) -> None:
    """Save buyers to JSON file."""
    file_path = os.path.join(data_dir, "buyers.json")
    save_json_file(file_path, [b.to_dict() for b in buyers])


def save_sellers(sellers: List[Seller], data_dir: str) -> None:
    """Save sellers to JSON file."""
    file_path = os.path.join(data_dir, "sellers.json")
    save_json_file(file_path, [s.to_dict() for s in sellers])


def save_disputes(disputes: List[Dispute], data_dir: str) -> None:
    """Save disputes to JSON file."""
    file_path = os.path.join(data_dir, "disputes.json")
    save_json_file(file_path, [d.to_dict() for d in disputes])


def save_fee_rules(fee_rules: FeeRules, data_dir: str) -> None:
    """Save fee rules to JSON file."""
    file_path = os.path.join(data_dir, "fee_rules.json")
    save_json_file(file_path, fee_rules.to_dict())


def save_all_data(data: Dict[str, Any], data_dir: str) -> None:
    """Save all auction data to the specified directory."""
    ensure_data_dir(data_dir)
    save_fee_rules(data["fee_rules"], data_dir)
    save_lots(data["lots"], data_dir)
    save_bids(data["bids"], data_dir)
    save_buyers(data["buyers"], data_dir)
    save_sellers(data["sellers"], data_dir)
    save_disputes(data["disputes"], data_dir)


def export_to_csv(data: List[Dict[str, Any]], file_path: str, fieldnames: List[str]) -> None:
    """Export data to a CSV file."""
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def export_settlements_to_csv(settlements: list, file_path: str) -> None:
    """Export lot settlements to CSV."""
    from .models import LotSettlement
    
    rows = []
    for s in settlements:
        row = {
            "lot_id": s.lot.lot_id,
            "lot_name": s.lot.name,
            "category": s.lot.category,
            "is_sold": s.is_sold,
            "sale_price": str(s.sale_price) if s.sale_price else "",
            "winning_buyer_id": s.winning_buyer.buyer_id if s.winning_buyer else "",
            "winning_buyer_name": s.winning_buyer.name if s.winning_buyer else "",
            "seller_id": s.lot.seller_id,
            "fees_total": str(sum(s.fees.values())) if s.fees else "",
            "buyer_total": str(s.buyer_total) if s.buyer_total else "",
            "seller_net": str(s.seller_net) if s.seller_net else "",
            "status": s.lot.status.value,
            "audit_flags": ";".join(s.audit_flags),
        }
        rows.append(row)
    
    fieldnames = [
        "lot_id", "lot_name", "category", "is_sold", "sale_price",
        "winning_buyer_id", "winning_buyer_name", "seller_id",
        "fees_total", "buyer_total", "seller_net", "status", "audit_flags"
    ]
    export_to_csv(rows, file_path, fieldnames)


def export_buyer_bills_to_csv(bills: list, file_path: str) -> None:
    """Export buyer bills to CSV."""
    rows = []
    for bill in bills:
        row = {
            "buyer_id": bill.buyer.buyer_id,
            "buyer_name": bill.buyer.name,
            "buyer_type": bill.buyer.type.value,
            "province": bill.buyer.province,
            "total_purchase": str(bill.total_purchase),
            "total_fees": str(bill.total_fees),
            "deposit_applied": str(bill.deposit_applied),
            "penalties": str(bill.penalties),
            "amount_due": str(bill.amount_due),
            "items_count": len(bill.settlements),
        }
        rows.append(row)
    
    fieldnames = [
        "buyer_id", "buyer_name", "buyer_type", "province",
        "total_purchase", "total_fees", "deposit_applied",
        "penalties", "amount_due", "items_count"
    ]
    export_to_csv(rows, file_path, fieldnames)


def export_seller_statements_to_csv(statements: list, file_path: str) -> None:
    """Export seller statements to CSV."""
    rows = []
    for stmt in statements:
        row = {
            "seller_id": stmt.seller.seller_id,
            "seller_name": stmt.seller.name,
            "province": stmt.seller.province,
            "total_sales": str(stmt.total_sales),
            "total_fees": str(stmt.total_fees),
            "penalties": str(stmt.penalties),
            "net_amount": str(stmt.net_amount),
            "items_count": len(stmt.settlements),
            "sold_count": sum(1 for s in stmt.settlements if s.is_sold),
        }
        rows.append(row)
    
    fieldnames = [
        "seller_id", "seller_name", "province", "total_sales",
        "total_fees", "penalties", "net_amount", "items_count", "sold_count"
    ]
    export_to_csv(rows, file_path, fieldnames)


def export_audit_findings_to_csv(findings: List[Dict[str, Any]], file_path: str) -> None:
    """Export audit findings to CSV."""
    fieldnames = [
        "type", "severity", "lot_id", "lot_name", "buyer_id", "buyer_name",
        "seller_id", "description", "recommendation", "suggested_status"
    ]
    export_to_csv(findings, file_path, fieldnames)


def initialize_sample_data(target_dir: Optional[str] = None) -> str:
    """Initialize the working directory with sample data."""
    from .sample_data.generate import save_sample_data
    
    if target_dir is None:
        target_dir = get_user_data_dir()
    
    ensure_data_dir(target_dir)
    save_sample_data(target_dir)
    
    return target_dir
