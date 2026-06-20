import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from auction_settle.models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules,
    LotStatus, InspectionGrade, BuyerType, DisputeType, DisputeStatus
)
from auction_settle.settlement import (
    is_bid_valid, rank_bids, process_lot_settlement, process_batch_settlement
)


@pytest.fixture
def sample_fee_rules():
    return FeeRules()


@pytest.fixture
def sample_buyers():
    return [
        Buyer(
            buyer_id="B001",
            name="Test Buyer 1",
            email="b1@test.com",
            type=BuyerType.INSTITUTION,
            province="北京",
            deposit_balance=Decimal("50000.00")
        ),
        Buyer(
            buyer_id="B002",
            name="Test Buyer 2",
            email="b2@test.com",
            type=BuyerType.INDIVIDUAL,
            province="上海",
            deposit_balance=Decimal("5000.00")
        ),
        Buyer(
            buyer_id="B003",
            name="Test Buyer 3",
            email="b3@test.com",
            type=BuyerType.BUSINESS,
            province="广东",
            deposit_balance=Decimal("8000.00"),
            is_high_risk=True
        ),
    ]


@pytest.fixture
def sample_sellers():
    return [
        Seller(
            seller_id="S001",
            name="Test Seller 1",
            email="s1@test.com",
            province="北京"
        ),
    ]


@pytest.fixture
def sample_lot():
    return Lot(
        lot_id="L001",
        name="Test Microscope",
        description="Test microscope",
        category="显微镜",
        serial_number="TEST-001",
        inspection_grade=InspectionGrade.A,
        estimated_value=Decimal("80000.00"),
        reserve_price=Decimal("50000.00"),
        requires_cold_chain=False,
        requires_wooden_crate=True,
        restrict_individual_buyers=False,
        allows_split_shipment=False,
        seller_id="S001",
        status=LotStatus.ACTIVE
    )


@pytest.fixture
def sample_lot_restricted():
    return Lot(
        lot_id="L002",
        name="Test HPLC",
        description="Test HPLC system",
        category="色谱仪",
        serial_number="TEST-002",
        inspection_grade=InspectionGrade.B,
        estimated_value=Decimal("120000.00"),
        reserve_price=Decimal("70000.00"),
        requires_cold_chain=False,
        requires_wooden_crate=True,
        restrict_individual_buyers=True,
        allows_split_shipment=True,
        seller_id="S001",
        status=LotStatus.ACTIVE
    )


@pytest.fixture
def sample_lot_withdrawn():
    base_time = datetime(2026, 6, 1, 10, 0, 0)
    return Lot(
        lot_id="L003",
        name="Withdrawn Lot",
        description="Withdrawn test lot",
        category="其他",
        serial_number="TEST-003",
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
        withdrawal_time=base_time + timedelta(days=1)
    )


@pytest.fixture
def sample_bids():
    base_time = datetime(2026, 6, 10, 9, 0, 0)
    return [
        Bid(
            bid_id="BID001",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("52000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
        Bid(
            bid_id="BID002",
            lot_id="L001",
            buyer_id="B002",
            amount=Decimal("55000.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID003",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("55000.00"),
            timestamp=base_time + timedelta(minutes=12)
        ),
        Bid(
            bid_id="BID004",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("45000.00"),
            timestamp=base_time + timedelta(minutes=5)
        ),
        Bid(
            bid_id="BID005",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=base_time + timedelta(minutes=20),
            is_withdrawn=True,
            withdrawal_reason="Changed mind",
            withdrawal_time=base_time + timedelta(minutes=21)
        ),
    ]


class TestBidRanking:
    def test_rank_bids_by_amount_descending(self, sample_bids):
        """Test that bids are ranked by amount descending."""
        ranked = rank_bids(sample_bids)
        amounts = [b.amount for b in ranked]
        assert amounts == sorted(amounts, reverse=True)

    def test_rank_bids_same_amount_earlier_first(self, sample_bids):
        """Test that bids with same amount are ranked by timestamp ascending."""
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids_same_price = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=20)
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B002",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=15)
            ),
        ]
        ranked = rank_bids(bids_same_price)
        assert ranked[0].bid_id == "BID2"
        assert ranked[1].bid_id == "BID1"

    def test_rank_bids_same_timestamp(self, sample_bids):
        """Test handling of bids with exact same timestamp."""
        base_time = datetime(2026, 6, 10, 9, 0, 0)
        bids_same_time = [
            Bid(
                bid_id="BID1",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("60000.00"),
                timestamp=base_time
            ),
            Bid(
                bid_id="BID2",
                lot_id="L001",
                buyer_id="B002",
                amount=Decimal("55000.00"),
                timestamp=base_time
            ),
        ]
        ranked = rank_bids(bids_same_time)
        assert ranked[0].amount == Decimal("60000.00")
        assert ranked[1].amount == Decimal("55000.00")


class TestBidValidity:
    def test_valid_bid(self, sample_lot, sample_buyers, sample_fee_rules):
        """Test that a valid bid passes validation."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot, sample_buyers[0], [], sample_fee_rules)
        assert is_valid is True
        assert reason is None
        assert rule is None

    def test_withdrawn_bid_invalid(self, sample_lot, sample_buyers, sample_fee_rules):
        """Test that a withdrawn bid is invalid."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0),
            is_withdrawn=True
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot, sample_buyers[0], [], sample_fee_rules)
        assert is_valid is False
        assert "撤回" in reason
        assert rule == "RULE_WITHDRAWN_BID"

    def test_below_reserve_price_invalid(self, sample_lot, sample_buyers, sample_fee_rules):
        """Test that a bid below reserve price is invalid."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("40000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot, sample_buyers[0], [], sample_fee_rules)
        assert is_valid is False
        assert "保留价" in reason
        assert rule == "RULE_RESERVE_PRICE"

    def test_individual_buyer_restricted(self, sample_lot_restricted, sample_buyers, sample_fee_rules):
        """Test that individual buyers are restricted from certain lots."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L002",
            buyer_id="B002",
            amount=Decimal("80000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot_restricted, sample_buyers[1], [], sample_fee_rules)
        assert is_valid is False
        assert "个人买家" in reason
        assert rule == "RULE_INDIVIDUAL_RESTRICTED"

    def test_high_risk_buyer_insufficient_deposit(self, sample_lot, sample_buyers, sample_fee_rules):
        """Test that high-risk buyers with insufficient deposit are rejected."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L001",
            buyer_id="B003",
            amount=Decimal("60000.00"),
            timestamp=datetime(2026, 6, 10, 9, 0, 0)
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot, sample_buyers[2], [], sample_fee_rules)
        assert is_valid is False
        assert "保证金不足" in reason
        assert rule == "RULE_INSUFFICIENT_DEPOSIT"

    def test_withdrawn_lot_bid_invalid(self, sample_lot_withdrawn, sample_buyers, sample_fee_rules):
        """Test that bids on withdrawn lots are invalid."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L003",
            buyer_id="B001",
            amount=Decimal("15000.00"),
            timestamp=sample_lot_withdrawn.withdrawal_time + timedelta(minutes=10)
        )
        is_valid, reason, rule = is_bid_valid(bid, sample_lot_withdrawn, sample_buyers[0], [], sample_fee_rules)
        assert is_valid is False
        assert "撤拍" in reason
        assert rule == "RULE_LOT_WITHDRAWN"

    def test_bid_before_withdrawal_valid(self, sample_lot_withdrawn, sample_buyers, sample_fee_rules):
        """Test that bids placed before lot withdrawal are still valid."""
        bid = Bid(
            bid_id="BID001",
            lot_id="L003",
            buyer_id="B001",
            amount=Decimal("15000.00"),
            timestamp=sample_lot_withdrawn.withdrawal_time - timedelta(hours=1)
        )
        is_valid, _, _ = is_bid_valid(bid, sample_lot_withdrawn, sample_buyers[0], [], sample_fee_rules)
        assert is_valid is False
        assert sample_lot_withdrawn.status == LotStatus.WITHDRAWN


class TestLotSettlement:
    def test_lot_settlement_normal(self, sample_lot, sample_bids, sample_buyers, sample_sellers, sample_fee_rules):
        """Test normal lot settlement process."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        disputes = []

        settlement = process_lot_settlement(
            sample_lot, sample_bids, buyer_map, seller_map, disputes, sample_fee_rules
        )

        assert settlement.is_sold is True
        assert settlement.sale_price == Decimal("55000.00")
        assert settlement.winning_bid is not None
        assert settlement.winning_bid.bid_id == "BID003"
        assert settlement.winning_buyer.buyer_id == "B001"

    def test_lot_settlement_withdrawn_lot(self, sample_lot_withdrawn, sample_bids, sample_buyers, sample_sellers, sample_fee_rules):
        """Test settlement for a withdrawn lot."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        disputes = []

        lot_bids = [
            Bid(
                bid_id="BID001",
                lot_id="L003",
                buyer_id="B001",
                amount=Decimal("15000.00"),
                timestamp=sample_lot_withdrawn.withdrawal_time - timedelta(hours=1)
            )
        ]

        settlement = process_lot_settlement(
            sample_lot_withdrawn, lot_bids, buyer_map, seller_map, disputes, sample_fee_rules
        )

        assert settlement.is_sold is False
        assert settlement.lot.status == LotStatus.WITHDRAWN
        assert len(settlement.excluded_bids) == 1
        assert "LOT_WITHDRAWN" in settlement.audit_flags

    def test_lot_settlement_no_valid_bids(self, sample_lot, sample_buyers, sample_sellers, sample_fee_rules):
        """Test settlement when no valid bids exist."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        disputes = []

        low_bids = [
            Bid(
                bid_id="BID001",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("40000.00"),
                timestamp=datetime(2026, 6, 10, 9, 0, 0)
            )
        ]

        settlement = process_lot_settlement(
            sample_lot, low_bids, buyer_map, seller_map, disputes, sample_fee_rules
        )

        assert settlement.is_sold is False
        assert len(settlement.excluded_bids) == 1
        assert "UNSOLD_NO_VALID_BIDS" in settlement.audit_flags

    def test_lot_settlement_tie_breaker(self, sample_lot, sample_buyers, sample_sellers, sample_fee_rules):
        """Test that tie is broken by earlier bid."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        disputes = []

        base_time = datetime(2026, 6, 10, 9, 0, 0)
        tie_bids = [
            Bid(
                bid_id="BID001",
                lot_id="L001",
                buyer_id="B001",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=20)
            ),
            Bid(
                bid_id="BID002",
                lot_id="L001",
                buyer_id="B002",
                amount=Decimal("55000.00"),
                timestamp=base_time + timedelta(minutes=15)
            ),
        ]

        settlement = process_lot_settlement(
            sample_lot, tie_bids, buyer_map, seller_map, disputes, sample_fee_rules
        )

        assert settlement.winning_bid.bid_id == "BID002"
        assert any("更早出价" in line for line in settlement.explanation)

    def test_excluded_bids_tracked(self, sample_lot, sample_bids, sample_buyers, sample_sellers, sample_fee_rules):
        """Test that excluded bids are properly tracked with reasons."""
        buyer_map = {b.buyer_id: b for b in sample_buyers}
        seller_map = {s.seller_id: s for s in sample_sellers}
        disputes = []

        settlement = process_lot_settlement(
            sample_lot, sample_bids, buyer_map, seller_map, disputes, sample_fee_rules
        )

        excluded_rules = [be.rule for be in settlement.excluded_bids]
        assert "RULE_RESERVE_PRICE" in excluded_rules
        assert "RULE_WITHDRAWN_BID" in excluded_rules


class TestBatchSettlement:
    def test_batch_settlement_multiple_lots(self, sample_lot, sample_lot_restricted, sample_bids, sample_buyers, sample_sellers, sample_fee_rules):
        """Test batch settlement with multiple lots."""
        disputes = []
        lots = [sample_lot, sample_lot_restricted]

        restricted_bids = [
            Bid(
                bid_id="BID100",
                lot_id="L002",
                buyer_id="B001",
                amount=Decimal("75000.00"),
                timestamp=datetime(2026, 6, 10, 9, 0, 0)
            )
        ]

        all_bids = sample_bids + restricted_bids

        settlements, audit_findings = process_batch_settlement(
            "TEST-BATCH",
            lots,
            all_bids,
            sample_buyers,
            sample_sellers,
            disputes,
            sample_fee_rules
        )

        assert len(settlements) == 2
        assert settlements[0].lot.lot_id == "L001"
        assert settlements[1].lot.lot_id == "L002"
        assert settlements[0].is_sold is True
        assert settlements[1].is_sold is True
