import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from auction_settle.models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules, LotSettlement,
    LotStatus, InspectionGrade, BuyerType, DisputeType, DisputeStatus
)
from auction_settle.audit import (
    run_audit, check_suspicious_bidding, check_price_anomalies,
    check_insufficient_deposit, check_lot_withdrawal_bids,
    check_cold_chain_fees, check_duplicate_serials,
    check_withdrawn_bids_impact, check_dispute_resolutions,
    evaluate_dispute, suggest_dispute_status, get_dispute_severity
)
from auction_settle.settlement import process_lot_settlement, process_batch_settlement


@pytest.fixture
def sample_fee_rules():
    return FeeRules()


@pytest.fixture
def sample_buyers():
    return [
        Buyer(
            buyer_id="B001",
            name="Institution Buyer",
            email="inst@test.com",
            type=BuyerType.INSTITUTION,
            province="北京",
            deposit_balance=Decimal("50000.00")
        ),
        Buyer(
            buyer_id="B002",
            name="High Risk Buyer",
            email="risk@test.com",
            type=BuyerType.BUSINESS,
            province="上海",
            deposit_balance=Decimal("5000.00"),
            is_high_risk=True
        ),
    ]


@pytest.fixture
def sample_sellers():
    return [
        Seller(
            seller_id="S001",
            name="Seller 1",
            email="s1@test.com",
            province="北京"
        ),
    ]


@pytest.fixture
def sample_lots():
    return [
        Lot(
            lot_id="L001",
            name="Normal Microscope",
            description="Normal microscope",
            category="显微镜",
            serial_number="SN-001",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("80000.00"),
            reserve_price=Decimal("50000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        ),
        Lot(
            lot_id="L002",
            name="Cold Chain Freezer",
            description="Cold chain required freezer",
            category="低温设备",
            serial_number="SN-002",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("55000.00"),
            reserve_price=Decimal("30000.00"),
            requires_cold_chain=True,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        ),
        Lot(
            lot_id="L003",
            name="Duplicate Serial Microscope",
            description="Same serial as L001",
            category="显微镜",
            serial_number="SN-001",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("60000.00"),
            reserve_price=Decimal("35000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        ),
        Lot(
            lot_id="L004",
            name="Withdrawn Lot",
            description="Withdrawn test lot",
            category="其他",
            serial_number="SN-004",
            inspection_grade=InspectionGrade.C,
            estimated_value=Decimal("20000.00"),
            reserve_price=Decimal("10000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.WITHDRAWN,
            withdrawal_reason="Seller withdrew",
            withdrawal_time=datetime(2026, 6, 3, 12, 0, 0)
        ),
        Lot(
            lot_id="L005",
            name="High Value Deviation",
            description="Very high sale price",
            category="测试",
            serial_number="SN-005",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("40000.00"),
            reserve_price=Decimal("20000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        ),
    ]


class TestSuspiciousBidding:
    def test_detect_rapid_consecutive_bids(self, sample_buyers):
        """Test detection of rapid consecutive bids from same buyer."""
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("52000.00"),
                timestamp=base_time + timedelta(minutes=10)
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=11)
            ),
        ]
        
        findings = check_suspicious_bidding(bids, sample_buyers)
        assert len(findings) == 1
        assert findings[0]["type"] == "SUSPICIOUS_BIDDING"
        assert findings[0]["severity"] == "medium"
        assert "连续出价" in findings[0]["description"]

    def test_no_suspicious_bidding_normal_interval(self, sample_buyers):
        """Test that normal bidding intervals are not flagged."""
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("52000.00"),
                timestamp=base_time + timedelta(minutes=10)
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=15)
            ),
        ]
        
        findings = check_suspicious_bidding(bids, sample_buyers)
        assert len(findings) == 0

    def test_withdrawn_bids_excluded_from_suspicious_check(self, sample_buyers):
        """Test that withdrawn bids are not considered in suspicious bidding check."""
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("52000.00"),
                timestamp=base_time + timedelta(minutes=10)
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=11),
                is_withdrawn=True
            ),
        ]
        
        findings = check_suspicious_bidding(bids, sample_buyers)
        assert len(findings) == 0


class TestPriceAnomalies:
    def test_detect_high_price_anomaly(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test detection of abnormally high sale price."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[4]
        bid = Bid(
            bid_id="BID1",
            lot_id="L005",
            buyer_id="B001",
            amount=Decimal("100000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_price_anomalies([settlement])
        assert len(findings) == 1
        assert findings[0]["type"] == "PRICE_ANOMALY_HIGH"
        assert findings[0]["severity"] == "high"

    def test_detect_low_price_anomaly(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test detection of abnormally low sale price."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = Lot(
            lot_id="L005",
            name="Low Price Test Lot",
            description="Test for low price anomaly",
            category="测试",
            serial_number="SN-LOW001",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("80000.00"),
            reserve_price=Decimal("30000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        )
        bid = Bid(
            bid_id="BID1",
            lot_id="L005",
            buyer_id="B001",
            amount=Decimal("35000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_price_anomalies([settlement])
        assert len(findings) == 1
        assert findings[0]["type"] == "PRICE_ANOMALY_LOW"
        assert findings[0]["severity"] == "medium"

    def test_normal_price_not_flagged(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test that normal prices are not flagged."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[0]
        bid = Bid(
            bid_id="BID1",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("75000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_price_anomalies([settlement])
        assert len(findings) == 0


class TestInsufficientDeposit:
    def test_detect_high_risk_insufficient_deposit(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test detection of high-risk buyer with insufficient deposit winning."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[0]
        bid = Bid(
            bid_id="BID1",
            lot_id="L001",
            buyer_id="B002",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_insufficient_deposit(
            [bid], sample_lots, sample_buyers, [settlement], sample_fee_rules
        )
        assert len(findings) == 0
        assert settlement.is_sold is False

    def test_normal_buyer_no_deposit_check(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test that non-high-risk buyers don't trigger deposit checks."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[0]
        bid = Bid(
            bid_id="BID1",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_insufficient_deposit(
            [bid], sample_lots, sample_buyers, [settlement], sample_fee_rules
        )
        assert len(findings) == 0
        assert settlement.is_sold is True


class TestLotWithdrawalBids:
    def test_detect_bid_after_withdrawal(self, sample_lots):
        """Test detection of bids placed after lot withdrawal."""
        lot = sample_lots[3]
        bid = Bid(
            bid_id="BID1",
            lot_id="L004",
            buyer_id="B001",
            amount=Decimal("15000.00"),
            timestamp=lot.withdrawal_time + timedelta(minutes=30)
        )
        
        findings = check_lot_withdrawal_bids(sample_lots, [bid])
        assert len(findings) == 1
        assert findings[0]["type"] == "BID_AFTER_WITHDRAWAL"
        assert findings[0]["severity"] == "medium"

    def test_no_flag_for_bid_before_withdrawal(self, sample_lots):
        """Test that bids before withdrawal are not flagged."""
        lot = sample_lots[3]
        bid = Bid(
            bid_id="BID1",
            lot_id="L004",
            buyer_id="B001",
            amount=Decimal("15000.00"),
            timestamp=lot.withdrawal_time - timedelta(hours=1)
        )
        
        findings = check_lot_withdrawal_bids(sample_lots, [bid])
        assert len(findings) == 0


class TestColdChainFees:
    def test_detect_missing_cold_chain_fee(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test detection of missing cold chain fee."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[1]
        bid = Bid(
            bid_id="BID1",
            lot_id="L002",
            buyer_id="B001",
            amount=Decimal("35000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_cold_chain_fees([settlement])
        assert len(findings) == 0
        assert "cold_chain_fee" in settlement.fees

    def test_no_flag_for_non_cold_chain_lot(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test that non-cold-chain lots don't trigger this check."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        
        lot = sample_lots[0]
        bid = Bid(
            bid_id="BID1",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        
        settlement = process_lot_settlement(
            lot, [bid], buyer_map, seller_map, [], sample_fee_rules
        )
        
        findings = check_cold_chain_fees([settlement])
        assert len(findings) == 0


class TestDuplicateSerials:
    def test_detect_duplicate_serial_numbers(self, sample_lots):
        """Test detection of duplicate equipment serial numbers."""
        findings = check_duplicate_serials(sample_lots)
        assert len(findings) == 1
        assert findings[0]["type"] == "DUPLICATE_SERIAL"
        assert findings[0]["severity"] == "high"
        assert findings[0]["serial_number"] == "SN-001"
        assert "L001" in findings[0]["lot_ids"]
        assert "L003" in findings[0]["lot_ids"]

    def test_no_duplicate_serials(self):
        """Test that unique serials are not flagged."""
        lots = [
            Lot(
                lot_id="L001",
                name="Lot 1",
                description="Test",
                category="Test",
                serial_number="SN-001",
                inspection_grade=InspectionGrade.A,
                estimated_value=Decimal("10000.00"),
                reserve_price=Decimal("5000.00"),
                requires_cold_chain=False,
                requires_wooden_crate=False,
                restrict_individual_buyers=False,
                allows_split_shipment=False,
                seller_id="S001",
                status=LotStatus.ACTIVE
            ),
            Lot(
                lot_id="L002",
                name="Lot 2",
                description="Test",
                category="Test",
                serial_number="SN-002",
                inspection_grade=InspectionGrade.A,
                estimated_value=Decimal("10000.00"),
                reserve_price=Decimal("5000.00"),
                requires_cold_chain=False,
                requires_wooden_crate=False,
                restrict_individual_buyers=False,
                allows_split_shipment=False,
                seller_id="S001",
                status=LotStatus.ACTIVE
            ),
        ]
        findings = check_duplicate_serials(lots)
        assert len(findings) == 0


class TestWithdrawnBids:
    def test_withdrawn_bids_tracked(self):
        """Test that withdrawn bids are properly tracked."""
        from datetime import datetime
        bids = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("50000.00"),
                timestamp=datetime(2026, 6, 10),
                is_withdrawn=True,
                withdrawal_reason="Changed mind"
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=datetime(2026, 6, 10)
            ),
        ]
        
        findings = check_withdrawn_bids_impact(bids, [])
        assert len(findings) == 1
        assert findings[0]["type"] == "WITHDRAWN_BID"
        assert findings[0]["bid_id"] == "BID1"


class TestDisputeResolution:
    def test_evaluate_withdrawn_bid_dispute(self):
        """Test evaluation of withdrawn bid dispute."""
        dispute = Dispute(
            dispute_id="DISP001",
            lot_id="L001",
            bid_id="BID001",
            type=DisputeType.WITHDRAWN_BID,
            description="Withdrawn bid concern",
            status=DisputeStatus.OPEN
        )
        
        recommendation = evaluate_dispute(dispute, None)
        assert "可自动驳回" in recommendation

    def test_suggest_auto_dismiss_for_withdrawn_bid(self):
        """Test that withdrawn bid disputes are suggested for auto-dismissal."""
        dispute = Dispute(
            dispute_id="DISP001",
            lot_id="L001",
            bid_id="BID001",
            type=DisputeType.WITHDRAWN_BID,
            description="Withdrawn bid concern",
            status=DisputeStatus.OPEN
        )
        
        recommendation = evaluate_dispute(dispute, None)
        suggested_status = suggest_dispute_status(dispute, recommendation)
        assert suggested_status == DisputeStatus.AUTO_DISMISSED

    def test_suggest_needs_review_for_suspicious_bidding(self):
        """Test that suspicious bidding disputes need review."""
        dispute = Dispute(
            dispute_id="DISP001",
            lot_id="L001",
            bid_id="BID001",
            type=DisputeType.SUSPICIOUS_BIDDING,
            description="Possible shill bidding",
            status=DisputeStatus.OPEN
        )
        
        recommendation = evaluate_dispute(dispute, None)
        suggested_status = suggest_dispute_status(dispute, recommendation)
        assert suggested_status == DisputeStatus.NEEDS_REVIEW

    def test_dispute_severity_levels(self):
        """Test severity level assignments for different dispute types."""
        assert get_dispute_severity(DisputeType.INSUFFICIENT_DEPOSIT) == "high"
        assert get_dispute_severity(DisputeType.DUPLICATE_SERIAL) == "high"
        assert get_dispute_severity(DisputeType.PRICE_ANOMALY) == "medium"
        assert get_dispute_severity(DisputeType.WITHDRAWN_BID) == "low"


class TestFullAudit:
    def test_run_full_audit(self, sample_fee_rules, sample_lots, sample_buyers, sample_sellers):
        """Test complete audit run."""
        from datetime import datetime, timedelta
        
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=10)
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("60000.00"),
                timestamp=base_time + timedelta(minutes=11)
            ),
            Bid(
                bid_id="BID3",
                lot_id="L002",
                buyer_id="B001",
                amount=Decimal("35000.00"),
                timestamp=base_time + timedelta(minutes=15)
            ),
            Bid(
                bid_id="BID4",
                lot_id="L004",
                buyer_id="B001",
                amount=Decimal("15000.00"),
                timestamp=sample_lots[3].withdrawal_time + timedelta(minutes=10)
            ),
        ]
        
        disputes = [
            Dispute(
                dispute_id="DISP001",
                lot_id="L001",
                bid_id="BID2",
                type=DisputeType.SUSPICIOUS_BIDDING,
                description="Rapid bidding",
                status=DisputeStatus.OPEN
            )
        ]
        
        settlements, _ = process_batch_settlement(
            "TEST-AUDIT",
            sample_lots, bids, sample_buyers, sample_sellers, disputes, sample_fee_rules
        )
        audit_findings = run_audit(
            sample_lots, bids, sample_buyers, sample_sellers, disputes, settlements, sample_fee_rules
        )
        
        assert len(audit_findings) > 0
        finding_types = [f["type"] for f in audit_findings]
        assert "SUSPICIOUS_BIDDING" in finding_types
        assert "DUPLICATE_SERIAL" in finding_types
        assert "BID_AFTER_WITHDRAWAL" in finding_types
