import json
import os
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules,
    LotStatus, InspectionGrade, DisputeType, DisputeStatus, BuyerType
)


def generate_fee_rules() -> FeeRules:
    return FeeRules()


def generate_sellers() -> List[Seller]:
    return [
        Seller(
            seller_id="S001",
            name="清华大学生物医学仪器实验室",
            email="lab@tsinghua.edu.cn",
            province="北京",
            phone="010-12345678"
        ),
        Seller(
            seller_id="S002",
            name="上海医疗器械有限公司",
            email="sales@sh-medical.com",
            province="上海",
            phone="021-87654321"
        ),
        Seller(
            seller_id="S003",
            name="广州科研设备调剂中心",
            email="equipment@gz-research.com",
            province="广东",
            phone="020-11112222"
        ),
    ]


def generate_buyers() -> List[Buyer]:
    return [
        Buyer(
            buyer_id="B001",
            name="北京协和医院采购部",
            email="purchase@pumch.cn",
            type=BuyerType.INSTITUTION,
            province="北京",
            deposit_balance=Decimal("50000.00"),
            is_high_risk=False,
            phone="010-88888888"
        ),
        Buyer(
            buyer_id="B002",
            name="上海生物科技有限公司",
            email="buy@sh-biotech.com",
            type=BuyerType.BUSINESS,
            province="上海",
            deposit_balance=Decimal("30000.00"),
            is_high_risk=False,
            phone="021-66666666"
        ),
        Buyer(
            buyer_id="B003",
            name="张明 (个人买家)",
            email="zhangming@example.com",
            type=BuyerType.INDIVIDUAL,
            province="江苏",
            deposit_balance=Decimal("5000.00"),
            is_high_risk=False,
            phone="13800138001"
        ),
        Buyer(
            buyer_id="B004",
            name="广州医疗器械贸易公司",
            email="trade@gz-med.com",
            type=BuyerType.BUSINESS,
            province="广东",
            deposit_balance=Decimal("15000.00"),
            is_high_risk=True,
            phone="020-77777777"
        ),
        Buyer(
            buyer_id="B005",
            name="李华 (个人买家)",
            email="lihua@example.com",
            type=BuyerType.INDIVIDUAL,
            province="浙江",
            deposit_balance=Decimal("2000.00"),
            is_high_risk=False,
            phone="13900139002"
        ),
    ]


def generate_lots() -> List[Lot]:
    base_time = datetime(2026, 6, 1, 10, 0, 0)
    return [
        Lot(
            lot_id="L1001",
            name="Olympus BX53 正置显微镜",
            description="二手Olympus BX53荧光显微镜，配置DAPI/FITC/TRITC荧光通道，使用年限5年",
            category="显微镜",
            serial_number="OLY-2021-BX53-001",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("85000.00"),
            reserve_price=Decimal("50000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE,
            location="北京"
        ),
        Lot(
            lot_id="L1002",
            name="Eppendorf 5810R 高速冷冻离心机",
            description="Eppendorf 5810R 大容量冷冻离心机，带4×750ml转子，温度范围-20~40℃",
            category="离心机",
            serial_number="EPP-2020-5810R-023",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("45000.00"),
            reserve_price=Decimal("25000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE,
            location="北京"
        ),
        Lot(
            lot_id="L1003",
            name="Tektronix MSO5104 混合信号示波器",
            description="Tektronix MSO5104示波器，1GHz带宽，4+16通道，触摸屏操作",
            category="示波器",
            serial_number="TEK-2022-MSO5104-156",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("65000.00"),
            reserve_price=Decimal("35000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S002",
            status=LotStatus.ACTIVE,
            location="上海"
        ),
        Lot(
            lot_id="L1004",
            name="Thermo Scientific 3111 二氧化碳培养箱",
            description="Thermo 3111 直热式CO2培养箱，184L容积，HEPA过滤，温度精度±0.1℃",
            category="恒温箱",
            serial_number="THM-2019-3111-089",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("38000.00"),
            reserve_price=Decimal("20000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S002",
            status=LotStatus.ACTIVE,
            location="上海"
        ),
        Lot(
            lot_id="L1005",
            name="Agilent 1260 高效液相色谱仪",
            description="Agilent 1260 HPLC系统，包括四元泵、自动进样器、柱温箱、DAD检测器",
            category="色谱仪",
            serial_number="AGL-2020-1260-234",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("120000.00"),
            reserve_price=Decimal("70000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=True,
            allows_split_shipment=True,
            seller_id="S003",
            status=LotStatus.ACTIVE,
            location="广州"
        ),
        Lot(
            lot_id="L1006",
            name="-80℃ 超低温冰箱",
            description="Thermo Scientific TSX600 -80℃超低温冰箱，568L容量，双压缩机系统，需冷链运输",
            category="低温设备",
            serial_number="THM-2021-TSX600-145",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("55000.00"),
            reserve_price=Decimal("30000.00"),
            requires_cold_chain=True,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S003",
            status=LotStatus.ACTIVE,
            location="广州"
        ),
        Lot(
            lot_id="L1007",
            name="Sartorius BSA224S 分析天平",
            description="赛多利斯BSA224S万分之一分析天平，220g量程，0.1mg精度，带防风罩",
            category="天平",
            serial_number="SAR-2022-BSA224S-078",
            inspection_grade=InspectionGrade.A,
            estimated_value=Decimal("18000.00"),
            reserve_price=Decimal("8000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=False,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S001",
            status=LotStatus.ACTIVE,
            location="北京"
        ),
        Lot(
            lot_id="L1008",
            name="Leica RM2235 石蜡切片机",
            description="Leica RM2235手动轮转切片机，切片厚度1~60μm，带废片槽",
            category="病理设备",
            serial_number="LEI-2020-RM2235-034",
            inspection_grade=InspectionGrade.C,
            estimated_value=Decimal("22000.00"),
            reserve_price=Decimal("10000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S002",
            status=LotStatus.WITHDRAWN,
            withdrawal_reason="卖家发现设备存在隐性故障",
            withdrawal_time=base_time + timedelta(days=2, hours=15),
            location="上海"
        ),
        Lot(
            lot_id="L1009",
            name="Millipore Milli-Q 超纯水系统",
            description="Millipore Milli-Q Integral 10超纯水系统，电阻率18.2MΩ·cm，产水量10L/h",
            category="纯化设备",
            serial_number="MIL-2019-MilliQ-112",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("42000.00"),
            reserve_price=Decimal("22000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S003",
            status=LotStatus.ACTIVE,
            location="广州"
        ),
        Lot(
            lot_id="L1010",
            name="Olympus BX53 正置显微镜 (重复序列号)",
            description="另一台Olympus BX53显微镜，故意使用重复序列号用于测试",
            category="显微镜",
            serial_number="OLY-2021-BX53-001",
            inspection_grade=InspectionGrade.B,
            estimated_value=Decimal("60000.00"),
            reserve_price=Decimal("35000.00"),
            requires_cold_chain=False,
            requires_wooden_crate=True,
            restrict_individual_buyers=False,
            allows_split_shipment=False,
            seller_id="S002",
            status=LotStatus.ACTIVE,
            location="上海"
        ),
    ]


def generate_bids() -> List[Bid]:
    base_time = datetime(2026, 6, 10, 9, 0, 0)
    return [
        Bid(
            bid_id="BID001",
            lot_id="L1001",
            buyer_id="B001",
            amount=Decimal("52000.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID002",
            lot_id="L1001",
            buyer_id="B002",
            amount=Decimal("55000.00"),
            timestamp=base_time + timedelta(minutes=20)
        ),
        Bid(
            bid_id="BID003",
            lot_id="L1001",
            buyer_id="B001",
            amount=Decimal("58000.00"),
            timestamp=base_time + timedelta(minutes=25)
        ),
        Bid(
            bid_id="BID004",
            lot_id="L1001",
            buyer_id="B001",
            amount=Decimal("60000.00"),
            timestamp=base_time + timedelta(minutes=26)
        ),
        Bid(
            bid_id="BID005",
            lot_id="L1001",
            buyer_id="B002",
            amount=Decimal("60000.00"),
            timestamp=base_time + timedelta(minutes=30)
        ),
        Bid(
            bid_id="BID006",
            lot_id="L1002",
            buyer_id="B003",
            amount=Decimal("20000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
        Bid(
            bid_id="BID007",
            lot_id="L1002",
            buyer_id="B004",
            amount=Decimal("26000.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID008",
            lot_id="L1002",
            buyer_id="B004",
            amount=Decimal("28000.00"),
            timestamp=base_time + timedelta(minutes=16),
            is_withdrawn=True,
            withdrawal_reason="买家操作失误",
            withdrawal_time=base_time + timedelta(minutes=17)
        ),
        Bid(
            bid_id="BID009",
            lot_id="L1002",
            buyer_id="B002",
            amount=Decimal("30000.00"),
            timestamp=base_time + timedelta(minutes=20)
        ),
        Bid(
            bid_id="BID010",
            lot_id="L1003",
            buyer_id="B005",
            amount=Decimal("30000.00"),
            timestamp=base_time + timedelta(minutes=5)
        ),
        Bid(
            bid_id="BID011",
            lot_id="L1003",
            buyer_id="B001",
            amount=Decimal("38000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
        Bid(
            bid_id="BID012",
            lot_id="L1003",
            buyer_id="B002",
            amount=Decimal("40000.00"),
            timestamp=base_time + timedelta(minutes=12)
        ),
        Bid(
            bid_id="BID013",
            lot_id="L1004",
            buyer_id="B003",
            amount=Decimal("18000.00"),
            timestamp=base_time + timedelta(minutes=8)
        ),
        Bid(
            bid_id="BID014",
            lot_id="L1004",
            buyer_id="B003",
            amount=Decimal("19000.00"),
            timestamp=base_time + timedelta(minutes=9)
        ),
        Bid(
            bid_id="BID015",
            lot_id="L1005",
            buyer_id="B003",
            amount=Decimal("75000.00"),
            timestamp=base_time + timedelta(minutes=20)
        ),
        Bid(
            bid_id="BID016",
            lot_id="L1005",
            buyer_id="B001",
            amount=Decimal("80000.00"),
            timestamp=base_time + timedelta(minutes=25)
        ),
        Bid(
            bid_id="BID017",
            lot_id="L1006",
            buyer_id="B004",
            amount=Decimal("32000.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID018",
            lot_id="L1006",
            buyer_id="B002",
            amount=Decimal("35000.00"),
            timestamp=base_time + timedelta(minutes=20)
        ),
        Bid(
            bid_id="BID019",
            lot_id="L1007",
            buyer_id="B005",
            amount=Decimal("7000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
        Bid(
            bid_id="BID020",
            lot_id="L1007",
            buyer_id="B003",
            amount=Decimal("8500.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID021",
            lot_id="L1007",
            buyer_id="B005",
            amount=Decimal("9000.00"),
            timestamp=base_time + timedelta(minutes=18)
        ),
        Bid(
            bid_id="BID022",
            lot_id="L1007",
            buyer_id="B005",
            amount=Decimal("9500.00"),
            timestamp=base_time + timedelta(minutes=18)
        ),
        Bid(
            bid_id="BID023",
            lot_id="L1008",
            buyer_id="B001",
            amount=Decimal("15000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
        Bid(
            bid_id="BID024",
            lot_id="L1008",
            buyer_id="B002",
            amount=Decimal("18000.00"),
            timestamp=base_time + timedelta(days=3, minutes=5)
        ),
        Bid(
            bid_id="BID025",
            lot_id="L1009",
            buyer_id="B004",
            amount=Decimal("25000.00"),
            timestamp=base_time + timedelta(minutes=15)
        ),
        Bid(
            bid_id="BID026",
            lot_id="L1009",
            buyer_id="B001",
            amount=Decimal("120000.00"),
            timestamp=base_time + timedelta(minutes=20)
        ),
        Bid(
            bid_id="BID027",
            lot_id="L1010",
            buyer_id="B002",
            amount=Decimal("40000.00"),
            timestamp=base_time + timedelta(minutes=10)
        ),
    ]


def generate_disputes() -> List[Dispute]:
    base_time = datetime(2026, 6, 15, 10, 0, 0)
    return [
        Dispute(
            dispute_id="DISP001",
            lot_id="L1001",
            bid_id="BID004",
            type=DisputeType.SUSPICIOUS_BIDDING,
            description="买家B001在1分钟内连续加价两次，可能存在抬价行为",
            status=DisputeStatus.OPEN,
            buyer_id="B001",
            created_at=base_time + timedelta(hours=1)
        ),
        Dispute(
            dispute_id="DISP002",
            lot_id="L1002",
            bid_id="BID008",
            type=DisputeType.WITHDRAWN_BID,
            description="买家B004撤回出价28000元，需要确认是否影响最终成交",
            status=DisputeStatus.AUTO_DISMISSED,
            buyer_id="B004",
            resolution_notes="撤回出价已自动排除，不影响成交结果",
            created_at=base_time + timedelta(hours=2),
            resolved_at=base_time + timedelta(hours=2, minutes=30)
        ),
        Dispute(
            dispute_id="DISP003",
            lot_id="L1007",
            bid_id=None,
            type=DisputeType.PRICE_ANOMALY,
            description="成交价9500元大幅低于估值18000元，需要复核",
            status=DisputeStatus.NEEDS_REVIEW,
            created_at=base_time + timedelta(hours=3)
        ),
        Dispute(
            dispute_id="DISP004",
            lot_id="L1009",
            bid_id="BID026",
            type=DisputeType.PRICE_ANOMALY,
            description="成交价120000元远高于估值42000元，可能存在异常出价",
            status=DisputeStatus.NEEDS_REVIEW,
            buyer_id="B001",
            created_at=base_time + timedelta(hours=4)
        ),
        Dispute(
            dispute_id="DISP005",
            lot_id="L1010",
            bid_id=None,
            type=DisputeType.DUPLICATE_SERIAL,
            description="设备序列号OLY-2021-BX53-001与L1001重复",
            status=DisputeStatus.OPEN,
            seller_id="S002",
            created_at=base_time + timedelta(hours=5)
        ),
        Dispute(
            dispute_id="DISP006",
            lot_id="L1005",
            bid_id="BID015",
            type=DisputeType.RESERVE_PRICE,
            description="买家B003为个人买家，参与了限制个人的拍品L1005",
            status=DisputeStatus.AUTO_DISMISSED,
            buyer_id="B003",
            resolution_notes="个人买家出价已自动排除，最终由B001成交",
            created_at=base_time + timedelta(hours=6),
            resolved_at=base_time + timedelta(hours=6, minutes=15)
        ),
    ]


def save_sample_data(output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    fee_rules = generate_fee_rules()
    sellers = generate_sellers()
    buyers = generate_buyers()
    lots = generate_lots()
    bids = generate_bids()
    disputes = generate_disputes()

    with open(os.path.join(output_dir, "fee_rules.json"), "w", encoding="utf-8") as f:
        json.dump(fee_rules.to_dict(), f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "sellers.json"), "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in sellers], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "buyers.json"), "w", encoding="utf-8") as f:
        json.dump([b.to_dict() for b in buyers], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "lots.json"), "w", encoding="utf-8") as f:
        json.dump([l.to_dict() for l in lots], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "bids.json"), "w", encoding="utf-8") as f:
        json.dump([b.to_dict() for b in bids], f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "disputes.json"), "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in disputes], f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    save_sample_data(data_dir)
    print(f"Sample data generated in {data_dir}")
