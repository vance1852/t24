import pytest
from decimal import Decimal

from auction_settle.models import (
    Lot, Bid, Buyer, Seller, FeeRules,
    LotStatus, InspectionGrade, BuyerType
)
from auction_settle.fees import (
    calculate_fees, calculate_buyer_bill, calculate_seller_statement, _round
)
from auction_settle.settlement import process_lot_settlement


@pytest.fixture
def fee_rules():
    return FeeRules()


@pytest.fixture
def buyer_beijing():
    return Buyer(
        buyer_id="B001",
        name="Beijing Buyer",
        email="beijing@test.com",
        type=BuyerType.INSTITUTION,
        province="北京",
        deposit_balance=Decimal("50000.00")
    )


@pytest.fixture
def buyer_shanghai():
    return Buyer(
        buyer_id="B002",
        name="Shanghai Buyer",
        email="shanghai@test.com",
        type=BuyerType.BUSINESS,
        province="上海",
        deposit_balance=Decimal("30000.00")
    )


@pytest.fixture
def seller_beijing():
    return Seller(
        seller_id="S001",
        name="Beijing Seller",
        email="seller@test.com",
        province="北京"
    )


@pytest.fixture
def seller_shanghai():
    return Seller(
        seller_id="S002",
        name="Shanghai Seller",
        email="seller2@test.com",
        province="上海"
    )


@pytest.fixture
def standard_lot():
    return Lot(
        lot_id="L001",
        name="Standard Microscope",
        description="Standard microscope",
        category="显微镜",
        serial_number="STD-001",
        inspection_grade=InspectionGrade.A,
        estimated_value=Decimal("80000.00"),
        reserve_price=Decimal("50000.00"),
        requires_cold_chain=False,
        requires_wooden_crate=False,
        restrict_individual_buyers=False,
        allows_split_shipment=False,
        seller_id="S001",
        status=LotStatus.ACTIVE
    )


@pytest.fixture
def cold_chain_lot():
    return Lot(
        lot_id="L002",
        name="Ultra Low Freezer",
        description="-80C freezer requiring cold chain",
        category="低温设备",
        serial_number="CC-001",
        inspection_grade=InspectionGrade.A,
        estimated_value=Decimal("55000.00"),
        reserve_price=Decimal("30000.00"),
        requires_cold_chain=True,
        requires_wooden_crate=True,
        restrict_individual_buyers=False,
        allows_split_shipment=False,
        seller_id="S001",
        status=LotStatus.ACTIVE
    )


@pytest.fixture
def split_shipment_lot():
    return Lot(
        lot_id="L003",
        name="HPLC System",
        description="Modular HPLC system",
        category="色谱仪",
        serial_number="SS-001",
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
def winning_bid():
    from datetime import datetime
    return Bid(
        bid_id="BID001",
        lot_id="L001",
        buyer_id="B001",
        amount=Decimal("60000.00"),
        timestamp=datetime(2026, 6, 10, 9, 0, 0)
    )


class TestDecimalPrecision:
    def test_round_half_up(self):
        """Test that rounding uses ROUND_HALF_UP."""
        assert _round(Decimal("1.234")) == Decimal("1.23")
        assert _round(Decimal("1.235")) == Decimal("1.24")
        assert _round(Decimal("1.236")) == Decimal("1.24")

    def test_no_float_in_calculations(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that all calculations use Decimal, not float."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        for fee_name, fee_amount in fees.items():
            assert isinstance(fee_amount, Decimal), f"{fee_name} is not Decimal"
            assert not isinstance(fee_amount, float), f"{fee_name} is float"

    def test_precision_maintained(self, fee_rules):
        """Test that precision is maintained through calculations."""
        from datetime import datetime
        lot = Lot(
            lot_id="L001",
            name="Test",
            description="Test",
            category="Test",
            serial_number="T1",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("100.00"),
            reserve_price=Decimal("50.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE
        )
        bid = Bid(
            bid_id="B1",
            lot_id="L001",
            buyer_id="B1",
            amount=Decimal("100.00"),
            timestamp=datetime(2026, 6, 10)
        )
        buyer = Buyer(
            buyer_id="B1",
            name="Test",
            email="test@test.com",
            type=BuyerType.INSTITUTION,
            province="北京",
            deposit_balance=Decimal("1000.00")
        )
        seller = Seller(
            seller_id="S1",
            name="Test",
            email="test@test.com",
            province="北京"
        )
        
        fees = calculate_fees(lot, bid, buyer, seller, fee_rules)
        
        platform_commission = Decimal("100.00") * Decimal("0.05")
        assert fees["platform_commission"] == _round(platform_commission)
        
        inspection_fee = Decimal("100.00") * Decimal("0.02")
        assert fees["inspection_fee"] == _round(inspection_fee)


class TestFeeCalculations:
    def test_platform_commission(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test platform commission calculation."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        expected_commission = Decimal("60000.00") * Decimal("0.05")
        assert fees["platform_commission"] == _round(expected_commission)

    def test_inspection_fee(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test inspection fee calculation."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        expected_inspection = Decimal("60000.00") * Decimal("0.02")
        assert fees["inspection_fee"] == _round(expected_inspection)

    def test_packaging_fee(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that packaging fee is always applied."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert fees["packaging_fee"] == Decimal("50.00")

    def test_cold_chain_fee_applied(self, fee_rules, cold_chain_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that cold chain fee is applied when required."""
        bid = Bid(
            bid_id="BID002",
            lot_id="L002",
            buyer_id="B001",
            amount=Decimal("35000.00"),
            timestamp=winning_bid.timestamp
        )
        fees = calculate_fees(cold_chain_lot, bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert "cold_chain_fee" in fees
        assert fees["cold_chain_fee"] == Decimal("200.00")

    def test_cold_chain_fee_not_applied(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that cold chain fee is not applied when not required."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert "cold_chain_fee" not in fees

    def test_wooden_crate_fee_applied(self, fee_rules, cold_chain_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that wooden crate fee is applied when required."""
        bid = Bid(
            bid_id="BID002",
            lot_id="L002",
            buyer_id="B001",
            amount=Decimal("35000.00"),
            timestamp=winning_bid.timestamp
        )
        fees = calculate_fees(cold_chain_lot, bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert "wooden_crate_fee" in fees
        assert fees["wooden_crate_fee"] == Decimal("150.00")

    def test_wooden_crate_fee_not_applied(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test that wooden crate fee is not applied when not required."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert "wooden_crate_fee" not in fees

    def test_intra_provincial_logistics(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test intra-provincial logistics fee."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert fees["logistics_fee"] == Decimal("100.00")

    def test_inter_provincial_logistics(self, fee_rules, standard_lot, winning_bid, buyer_shanghai, seller_beijing):
        """Test inter-provincial logistics fee."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_shanghai, seller_beijing, fee_rules)
        
        assert fees["logistics_fee"] == Decimal("300.00")

    def test_split_shipment_surcharge(self, fee_rules, split_shipment_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test split shipment surcharge."""
        bid = Bid(
            bid_id="BID003",
            lot_id="L003",
            buyer_id="B001",
            amount=Decimal("80000.00"),
            timestamp=winning_bid.timestamp
        )
        fees = calculate_fees(split_shipment_lot, bid, buyer_beijing, seller_beijing, fee_rules)
        
        assert "split_shipment_surcharge" in fees
        assert fees["split_shipment_surcharge"] == Decimal("50.00")

    def test_tax_calculation(self, fee_rules, standard_lot, winning_bid, buyer_beijing, seller_beijing):
        """Test tax calculation on taxable amount."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_beijing, seller_beijing, fee_rules)
        
        taxable_amount = (
            Decimal("60000.00") + 
            fees["inspection_fee"] + 
            fees["packaging_fee"] + 
            fees["logistics_fee"]
        )
        expected_tax = taxable_amount * Decimal("0.13")
        
        assert fees["tax"] == _round(expected_tax)

    def test_full_fee_breakdown(self, fee_rules, standard_lot, winning_bid, buyer_shanghai, seller_beijing):
        """Test complete fee breakdown for a typical transaction."""
        fees = calculate_fees(standard_lot, winning_bid, buyer_shanghai, seller_beijing, fee_rules)
        
        expected_fees = {
            "platform_commission": Decimal("60000.00") * Decimal("0.05"),
            "inspection_fee": Decimal("60000.00") * Decimal("0.02"),
            "packaging_fee": Decimal("50.00"),
            "logistics_fee": Decimal("300.00"),
        }
        
        taxable = (
            Decimal("60000.00") + 
            expected_fees["inspection_fee"] + 
            expected_fees["packaging_fee"] + 
            expected_fees["logistics_fee"]
        )
        expected_fees["tax"] = taxable * Decimal("0.13")
        
        for key, value in expected_fees.items():
            assert fees[key] == _round(value)


class TestBuyerBill:
    def test_buyer_bill_calculation(self, fee_rules, buyer_beijing, standard_lot, winning_bid, seller_beijing):
        """Test buyer bill calculation."""
        buyer_map = {buyer_beijing.buyer_id: buyer_beijing}
        seller_map = {seller_beijing.seller_id: seller_beijing}
        
        settlement = process_lot_settlement(
            standard_lot, [winning_bid], buyer_map, seller_map, [], fee_rules
        )
        
        bill = calculate_buyer_bill(buyer_beijing, [settlement], fee_rules)
        
        assert bill.buyer.buyer_id == buyer_beijing.buyer_id
        assert bill.total_purchase == Decimal("60000.00")
        
        buyer_fees = sum(
            v for k, v in settlement.fees.items()
            if k.startswith("buyer_") or k in [
                "inspection_fee", "packaging_fee", "logistics_fee", "tax"
            ]
        )
        assert bill.total_fees == _round(buyer_fees)
        
        assert bill.deposit_applied == min(buyer_beijing.deposit_balance, bill.total_purchase + bill.total_fees)
        assert bill.amount_due == bill.total_purchase + bill.total_fees - bill.deposit_applied

    def test_buyer_bill_multiple_items(self, fee_rules, buyer_beijing, standard_lot, cold_chain_lot, winning_bid, seller_beijing):
        """Test buyer bill with multiple items."""
        buyer_map = {buyer_beijing.buyer_id: buyer_beijing}
        seller_map = {seller_beijing.seller_id: seller_beijing}
        
        bid1 = Bid(
            bid_id="BID1",
            lot_id="L001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=winning_bid.timestamp
        )
        bid2 = Bid(
            bid_id="BID2",
            lot_id="L002",
            buyer_id="B001",
            amount=Decimal("35000.00"),
            timestamp=winning_bid.timestamp
        )
        
        settlement1 = process_lot_settlement(
            standard_lot, [bid1], buyer_map, seller_map, [], fee_rules
        )
        settlement2 = process_lot_settlement(
            cold_chain_lot, [bid2], buyer_map, seller_map, [], fee_rules
        )
        
        bill = calculate_buyer_bill(buyer_beijing, [settlement1, settlement2], fee_rules)
        
        assert len(bill.settlements) == 2
        assert bill.total_purchase == Decimal("95000.00")


class TestSellerStatement:
    def test_seller_statement_calculation(self, fee_rules, seller_beijing, standard_lot, winning_bid, buyer_beijing):
        """Test seller statement calculation."""
        buyer_map = {buyer_beijing.buyer_id: buyer_beijing}
        seller_map = {seller_beijing.seller_id: seller_beijing}
        
        settlement = process_lot_settlement(
            standard_lot, [winning_bid], buyer_map, seller_map, [], fee_rules
        )
        
        stmt = calculate_seller_statement(seller_beijing, [settlement], fee_rules)
        
        assert stmt.seller.seller_id == seller_beijing.seller_id
        assert stmt.total_sales == Decimal("60000.00")
        
        seller_fees = sum(
            v for k, v in settlement.fees.items()
            if k.startswith("seller_") or k == "platform_commission"
        )
        assert stmt.total_fees == _round(seller_fees)
        assert stmt.net_amount == stmt.total_sales - stmt.total_fees - stmt.penalties

    def test_seller_statement_withdrawn_lot_penalty(self, fee_rules, seller_beijing):
        """Test that seller withdrawal penalty is applied."""
        from datetime import datetime, timedelta
        
        withdrawn_lot = Lot(
            lot_id="L004",
            name="Withdrawn Lot",
            description="Withdrawn",
            category="Test",
            serial_number="W1",
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
            withdrawal_time=datetime(2026, 6, 2)
        )
        
        buyer_map = {}
        seller_map = {seller_beijing.seller_id: seller_beijing}
        
        settlement = process_lot_settlement(
            withdrawn_lot, [], buyer_map, seller_map, [], fee_rules
        )
        
        stmt = calculate_seller_statement(seller_beijing, [settlement], fee_rules)
        
        assert stmt.penalties == Decimal("200.00")
        assert stmt.net_amount == -Decimal("200.00")

    def test_seller_statement_mixed_lots(self, fee_rules, seller_beijing, standard_lot, winning_bid, buyer_beijing):
        """Test seller statement with sold and withdrawn lots."""
        from datetime import datetime, timedelta
        
        withdrawn_lot = Lot(
            lot_id="L004",
            name="Withdrawn Lot",
            description="Withdrawn",
            category="Test",
            serial_number="W1",
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
            withdrawal_time=datetime(2026, 6, 2)
        )
        
        buyer_map = {buyer_beijing.buyer_id: buyer_beijing}
        seller_map = {seller_beijing.seller_id: seller_beijing}
        
        settlement1 = process_lot_settlement(
            standard_lot, [winning_bid], buyer_map, seller_map, [], fee_rules
        )
        settlement2 = process_lot_settlement(
            withdrawn_lot, [], buyer_map, seller_map, [], fee_rules
        )
        
        stmt = calculate_seller_statement(seller_beijing, [settlement1, settlement2], fee_rules)
        
        assert len(stmt.settlements) == 2
        assert stmt.total_sales == Decimal("60000.00")
        assert stmt.penalties == Decimal("200.00")
        assert stmt.sold_count == 1
