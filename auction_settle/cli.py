import click
import json
import os
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any
from tabulate import tabulate

from . import __version__
from .models import (
    Lot, Bid, Buyer, Seller, Dispute, FeeRules, LotSettlement,
    BuyerBill, SellerStatement, BatchResult
)
from .data_loader import (
    load_all_data, initialize_sample_data, ensure_data_dir,
    export_settlements_to_csv, export_buyer_bills_to_csv,
    export_seller_statements_to_csv, export_audit_findings_to_csv,
    save_json_file
)
from .settlement import process_batch_settlement, process_lot_settlement
from .fees import calculate_buyer_bill, calculate_seller_statement
from .audit import run_audit


def format_decimal(value: Decimal) -> str:
    """Format a Decimal value for display."""
    return f"{value:,.2f}"


def print_table(data: List[List[Any]], headers: List[str], tablefmt: str = "simple") -> None:
    """Print a formatted table to the console."""
    click.echo(tabulate(data, headers=headers, tablefmt=tablefmt, stralign="left", numalign="right"))


def get_data_dir(data_dir: str) -> str:
    """Get the data directory, using default if not specified."""
    if data_dir:
        return os.path.abspath(data_dir)
    return os.path.join(os.getcwd(), "auction_data")


def load_data_with_default(data_dir: str) -> Dict[str, Any]:
    """Load data, falling back to sample data if user data doesn't exist."""
    user_dir = get_data_dir(data_dir)
    
    if os.path.exists(os.path.join(user_dir, "lots.json")):
        return load_all_data(user_dir)
    
    from .data_loader import get_default_data_dir
    return load_all_data(get_default_data_dir())


@click.group()
@click.version_option(version=__version__, prog_name="auction-settle")
@click.option("--data-dir", type=click.Path(), default=None, help="数据目录路径")
@click.pass_context
def main(ctx: click.Context, data_dir: str) -> None:
    """二手实验室设备拍卖结算与审计工具"""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir


@main.command()
@click.option("--data-dir", type=click.Path(), default=None, help="目标数据目录")
@click.option("--force", is_flag=True, help="强制覆盖现有数据")
@click.pass_context
def init(ctx: click.Context, data_dir: str, force: bool) -> None:
    """初始化样例数据到当前目录"""
    target_dir = get_data_dir(data_dir)
    data_file = os.path.join(target_dir, "lots.json")
    
    if os.path.exists(data_file) and not force:
        click.echo(f"错误: 数据目录已存在数据: {target_dir}")
        click.echo("使用 --force 参数强制覆盖")
        return
    
    target_dir = initialize_sample_data(target_dir)
    click.echo(f"[OK] 样例数据已初始化到: {target_dir}")
    click.echo("")
    click.echo("包含以下样例数据:")
    click.echo("  - 10 个拍品 (含显微镜、离心机、示波器、恒温箱等)")
    click.echo("  - 27 条出价记录 (含撤回、同价、低于保留价等边界情况)")
    click.echo("  - 5 位买家 (含个人、企业、机构)")
    click.echo("  - 3 位卖家")
    click.echo("  - 6 条争议记录")
    click.echo("  - 可配置的费用规则")


@main.command()
@click.option("--batch-id", default="BATCH-001", help="批次编号")
@click.option("--output-format", type=click.Choice(["table", "json", "csv"]), default="table", help="输出格式")
@click.option("--output", type=click.Path(), help="输出文件路径 (JSON/CSV格式时使用)")
@click.pass_context
def settle(ctx: click.Context, batch_id: str, output_format: str, output: str) -> None:
    """计算某个批次的成交结果"""
    data = load_data_with_default(ctx.obj["data_dir"])
    data_dir = get_data_dir(ctx.obj["data_dir"])
    
    click.echo(f"正在处理批次: {batch_id}")
    click.echo("")
    
    settlements, audit_findings = process_batch_settlement(
        batch_id,
        data["lots"],
        data["bids"],
        data["buyers"],
        data["sellers"],
        data["disputes"],
        data["fee_rules"]
    )
    
    total_sales = sum(
        (s.sale_price or Decimal("0")) for s in settlements if s.is_sold
    )
    total_fees = sum(
        sum(s.fees.values()) for s in settlements if s.is_sold
    )
    total_penalties = Decimal("0")
    
    batch_result = BatchResult(
        batch_id=batch_id,
        settlements=settlements,
        buyer_bills=[],
        seller_statements=[],
        total_sales=total_sales,
        total_fees=total_fees,
        total_penalties=total_penalties,
        audit_findings=audit_findings
    )
    
    if output_format == "json":
        output_path = output or f"settlement_{batch_id}.json"
        save_json_file(output_path, batch_result.to_dict())
        click.echo(f"[OK] 结算结果已导出到: {output_path}")
        return
    
    if output_format == "csv":
        output_path = output or f"settlement_{batch_id}.csv"
        export_settlements_to_csv(settlements, output_path)
        click.echo(f"[OK] 结算结果已导出到: {output_path}")
        return
    
    click.echo("=" * 80)
    click.echo(f"拍卖批次结算结果 - {batch_id}")
    click.echo("=" * 80)
    click.echo("")
    
    table_data = []
    for s in settlements:
        status = "[OK] 已成交" if s.is_sold else "[X] 未成交"
        if s.lot.status.value == "withdrawn":
            status = "[--] 已撤拍"
        
        sale_price = format_decimal(s.sale_price) if s.sale_price else "-"
        buyer_name = s.winning_buyer.name if s.winning_buyer else "-"
        buyer_total = format_decimal(s.buyer_total) if s.buyer_total else "-"
        seller_net = format_decimal(s.seller_net) if s.seller_net else "-"
        
        flags = ";".join(s.audit_flags[:2]) if s.audit_flags else ""
        if len(s.audit_flags) > 2:
            flags += f"...(+{len(s.audit_flags)-2})"
        
        table_data.append([
            s.lot.lot_id,
            s.lot.name[:30],
            status,
            sale_price,
            buyer_name[:15],
            buyer_total,
            seller_net,
            flags
        ])
    
    headers = [
        "拍品编号", "拍品名称", "状态", "成交价", 
        "买家", "买家应付", "卖家净得", "审计标记"
    ]
    print_table(table_data, headers)
    
    click.echo("")
    click.echo("=" * 80)
    click.echo("汇总统计")
    click.echo("=" * 80)
    
    sold_count = sum(1 for s in settlements if s.is_sold)
    withdrawn_count = sum(1 for s in settlements if s.lot.status.value == "withdrawn")
    unsold_count = len(settlements) - sold_count - withdrawn_count
    
    summary_data = [
        ["总拍品数", len(settlements)],
        ["已成交", sold_count],
        ["未成交", unsold_count],
        ["已撤拍", withdrawn_count],
        ["总成交额", format_decimal(total_sales) + " 元"],
        ["总费用", format_decimal(total_fees) + " 元"],
        ["审计发现", f"{len(audit_findings)} 项"],
    ]
    print_table(summary_data, ["指标", "数值"], tablefmt="plain")


@main.command()
@click.argument("buyer_id", required=False)
@click.option("--output-format", type=click.Choice(["table", "json", "csv"]), default="table", help="输出格式")
@click.option("--output", type=click.Path(), help="输出文件路径")
@click.pass_context
def buyer_bill(ctx: click.Context, buyer_id: str, output_format: str, output: str) -> None:
    """生成买家应付账单"""
    data = load_data_with_default(ctx.obj["data_dir"])
    
    click.echo("正在生成买家账单...")
    click.echo("")
    
    settlements, _ = process_batch_settlement(
        "BATCH-001",
        data["lots"],
        data["bids"],
        data["buyers"],
        data["sellers"],
        data["disputes"],
        data["fee_rules"]
    )
    
    if buyer_id:
        buyers = [b for b in data["buyers"] if b.buyer_id == buyer_id]
        if not buyers:
            click.echo(f"错误: 未找到买家 {buyer_id}")
            return
    else:
        buyers = data["buyers"]
    
    bills: List[BuyerBill] = []
    for buyer in buyers:
        bill = calculate_buyer_bill(buyer, settlements, data["fee_rules"])
        if bill.settlements or bill.penalties > 0:
            bills.append(bill)
    
    if not bills:
        click.echo("没有买家需要付款")
        return
    
    if output_format == "json":
        output_path = output or "buyer_bills.json"
        save_json_file(output_path, [b.to_dict() for b in bills])
        click.echo(f"[OK] 买家账单已导出到: {output_path}")
        return
    
    if output_format == "csv":
        output_path = output or "buyer_bills.csv"
        export_buyer_bills_to_csv(bills, output_path)
        click.echo(f"[OK] 买家账单已导出到: {output_path}")
        return
    
    for bill in bills:
        click.echo("=" * 80)
        click.echo(f"买家账单 - {bill.buyer.name} ({bill.buyer.buyer_id})")
        click.echo("=" * 80)
        click.echo(f"买家类型: {bill.buyer.type.value}    省份: {bill.buyer.province}")
        click.echo(f"保证金余额: {format_decimal(bill.buyer.deposit_balance)} 元")
        click.echo("")
        
        if bill.settlements:
            click.echo("拍品明细:")
            table_data = []
            for s in bill.settlements:
                fees = format_decimal(sum(v for k, v in s.fees.items() 
                    if k.startswith("buyer_") or k in 
                    ["inspection_fee", "packaging_fee", "cold_chain_fee", 
                     "wooden_crate_fee", "logistics_fee", "split_shipment_surcharge", "tax"]))
                total = format_decimal(s.buyer_total) if s.buyer_total else "-"
                table_data.append([
                    s.lot.lot_id,
                    s.lot.name[:30],
                    format_decimal(s.sale_price),
                    fees,
                    total
                ])
            headers = ["拍品编号", "拍品名称", "成交价", "费用", "小计"]
            print_table(table_data, headers)
        
        click.echo("")
        click.echo("-" * 80)
        summary_data = [
            ["购货款合计", format_decimal(bill.total_purchase) + " 元"],
            ["费用合计", format_decimal(bill.total_fees) + " 元"],
            ["保证金抵扣", "-" + format_decimal(bill.deposit_applied) + " 元"],
            ["罚款", format_decimal(bill.penalties) + " 元"],
            ["应付款总额", format_decimal(bill.amount_due) + " 元"],
        ]
        print_table(summary_data, ["项目", "金额"], tablefmt="plain")
        click.echo("")


@main.command()
@click.argument("seller_id", required=False)
@click.option("--output-format", type=click.Choice(["table", "json", "csv"]), default="table", help="输出格式")
@click.option("--output", type=click.Path(), help="输出文件路径")
@click.pass_context
def seller_statement(ctx: click.Context, seller_id: str, output_format: str, output: str) -> None:
    """生成卖家结算单"""
    data = load_data_with_default(ctx.obj["data_dir"])
    
    click.echo("正在生成卖家结算单...")
    click.echo("")
    
    settlements, _ = process_batch_settlement(
        "BATCH-001",
        data["lots"],
        data["bids"],
        data["buyers"],
        data["sellers"],
        data["disputes"],
        data["fee_rules"]
    )
    
    if seller_id:
        sellers = [s for s in data["sellers"] if s.seller_id == seller_id]
        if not sellers:
            click.echo(f"错误: 未找到卖家 {seller_id}")
            return
    else:
        sellers = data["sellers"]
    
    statements: List[SellerStatement] = []
    for seller in sellers:
        stmt = calculate_seller_statement(seller, settlements, data["fee_rules"])
        statements.append(stmt)
    
    if output_format == "json":
        output_path = output or "seller_statements.json"
        save_json_file(output_path, [s.to_dict() for s in statements])
        click.echo(f"[OK] 卖家结算单已导出到: {output_path}")
        return
    
    if output_format == "csv":
        output_path = output or "seller_statements.csv"
        export_seller_statements_to_csv(statements, output_path)
        click.echo(f"[OK] 卖家结算单已导出到: {output_path}")
        return
    
    for stmt in statements:
        click.echo("=" * 80)
        click.echo(f"卖家结算单 - {stmt.seller.name} ({stmt.seller.seller_id})")
        click.echo("=" * 80)
        click.echo(f"省份: {stmt.seller.province}    联系邮箱: {stmt.seller.email}")
        click.echo("")
        
        click.echo("拍品明细:")
        table_data = []
        for s in stmt.settlements:
            status = "已成交" if s.is_sold else "未成交"
            if s.lot.status.value == "withdrawn":
                status = "已撤拍"
            
            sale_price = format_decimal(s.sale_price) if s.sale_price else "-"
            fees = format_decimal(sum(v for k, v in s.fees.items() 
                if k.startswith("seller_") or k == "platform_commission"))
            
            table_data.append([
                s.lot.lot_id,
                s.lot.name[:30],
                status,
                sale_price,
                fees if s.is_sold else "-",
            ])
        headers = ["拍品编号", "拍品名称", "状态", "成交价", "平台费用"]
        print_table(table_data, headers)
        
        click.echo("")
        click.echo("-" * 80)
        summary_data = [
            ["销售总额", format_decimal(stmt.total_sales) + " 元"],
            ["平台费用合计", format_decimal(stmt.total_fees) + " 元"],
            ["罚款", format_decimal(stmt.penalties) + " 元"],
            ["净得金额", format_decimal(stmt.net_amount) + " 元"],
        ]
        print_table(summary_data, ["项目", "金额"], tablefmt="plain")
        click.echo("")


@main.command()
@click.option("--output-format", type=click.Choice(["table", "json", "csv"]), default="table", help="输出格式")
@click.option("--output", type=click.Path(), help="输出文件路径")
@click.option("--severity", type=click.Choice(["all", "high", "medium", "low"]), default="all", help="按严重程度过滤")
@click.pass_context
def audit(ctx: click.Context, output_format: str, output: str, severity: str) -> None:
    """检查异常和争议"""
    data = load_data_with_default(ctx.obj["data_dir"])
    
    click.echo("正在执行审计检查...")
    click.echo("")
    
    settlements, audit_findings = process_batch_settlement(
        "BATCH-001",
        data["lots"],
        data["bids"],
        data["buyers"],
        data["sellers"],
        data["disputes"],
        data["fee_rules"]
    )
    
    if severity != "all":
        audit_findings = [f for f in audit_findings if f.get("severity") == severity]
    
    if output_format == "json":
        output_path = output or "audit_findings.json"
        save_json_file(output_path, audit_findings)
        click.echo(f"[OK] 审计结果已导出到: {output_path}")
        return
    
    if output_format == "csv":
        output_path = output or "audit_findings.csv"
        export_audit_findings_to_csv(audit_findings, output_path)
        click.echo(f"[OK] 审计结果已导出到: {output_path}")
        return
    
    click.echo("=" * 80)
    click.echo(f"审计异常清单 - 共发现 {len(audit_findings)} 项问题")
    click.echo("=" * 80)
    click.echo("")
    
    if not audit_findings:
        click.echo("[OK] 未发现异常，所有结算正常")
        return
    
    severity_map = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}
    
    table_data = []
    for i, finding in enumerate(audit_findings, 1):
        sev = severity_map.get(finding.get("severity", "low"), "[LOW]")
        lot_id = finding.get("lot_id", "-")
        ftype = finding.get("type", "-")
        desc = finding.get("description", "")[:60]
        suggestion = finding.get("suggested_status", "")
        if suggestion:
            suggestion = suggestion.replace("_", " ")
        
        table_data.append([
            i, sev, ftype, lot_id, desc, suggestion
        ])
    
    headers = ["序号", "严重程度", "类型", "拍品", "描述", "建议状态"]
    print_table(table_data, headers)
    
    click.echo("")
    click.echo("详细信息:")
    click.echo("-" * 80)
    
    for i, finding in enumerate(audit_findings, 1):
        sev = severity_map.get(finding.get("severity", "low"), "[LOW]")
        click.echo("")
        click.echo(f"{i}. {sev} - {finding.get('type')}")
        click.echo(f"   拍品: {finding.get('lot_id', '-')}  {finding.get('lot_name', '')}")
        if finding.get("buyer_id"):
            click.echo(f"   买家: {finding.get('buyer_id')}  {finding.get('buyer_name', '')}")
        if finding.get("seller_id"):
            click.echo(f"   卖家: {finding.get('seller_id')}")
        click.echo(f"   描述: {finding.get('description')}")
        click.echo(f"   建议: {finding.get('recommendation')}")
        if finding.get("suggested_status"):
            status = finding.get("suggested_status").replace("_", " ")
            click.echo(f"   建议处理: {status}")


@main.command()
@click.argument("args", nargs=-1)
@click.option("--output-format", type=click.Choice(["table", "json"]), default="table", help="输出格式")
@click.option("--output", type=click.Path(), help="输出文件路径")
@click.pass_context
def explain(ctx: click.Context, args: tuple, output_format: str, output: str) -> None:
    """解释某个拍品的成交过程 (如: explain lot L1007)"""
    if len(args) == 0:
        click.echo("请提供拍品编号，例如: explain lot L1007 或 explain L1007")
        return
    
    if len(args) == 2 and args[0].lower() == "lot":
        lot_id = args[1]
    else:
        lot_id = args[-1]
    
    data = load_data_with_default(ctx.obj["data_dir"])
    buyer_map = {b.buyer_id: b for b in data["buyers"]}
    seller_map = {s.seller_id: s for s in data["sellers"]}
    
    lot = next((l for l in data["lots"] if l.lot_id == lot_id), None)
    if not lot:
        click.echo(f"错误: 未找到拍品 {lot_id}")
        return
    
    lot_bids = [b for b in data["bids"] if b.lot_id == lot_id]
    lot_disputes = [d for d in data["disputes"] if d.lot_id == lot_id]
    
    settlement = process_lot_settlement(
        lot, lot_bids, buyer_map, seller_map, lot_disputes, data["fee_rules"]
    )
    
    if output_format == "json":
        output_path = output or f"explain_{lot_id}.json"
        save_json_file(output_path, settlement.to_dict())
        click.echo(f"[OK] 拍品说明已导出到: {output_path}")
        return
    
    click.echo("=" * 80)
    click.echo(f"拍品成交说明 - {lot_id}: {lot.name}")
    click.echo("=" * 80)
    click.echo("")
    
    click.echo("[INFO] 拍品信息:")
    click.echo(f"  类别: {lot.category}")
    click.echo(f"  序列号: {lot.serial_number or '无'}")
    click.echo(f"  检测等级: {lot.inspection_grade.value}")
    click.echo(f"  估值: {format_decimal(lot.estimated_value)} 元")
    click.echo(f"  保留价: {format_decimal(lot.reserve_price)} 元")
    click.echo(f"  特殊要求: ", nl=False)
    reqs = []
    if lot.requires_cold_chain:
        reqs.append("冷链运输")
    if lot.requires_wooden_crate:
        reqs.append("木箱包装")
    if lot.restrict_individual_buyers:
        reqs.append("限制个人买家")
    if lot.allows_split_shipment:
        reqs.append("支持拆单")
    click.echo(", ".join(reqs) if reqs else "无")
    click.echo(f"  卖家: {seller_map[lot.seller_id].name}")
    click.echo("")
    
    click.echo("[BID] 出价记录:")
    all_bids = sorted(lot_bids, key=lambda b: b.timestamp)
    for bid in all_bids:
        buyer = buyer_map.get(bid.buyer_id)
        status = ""
        if bid.is_withdrawn:
            status = " [已撤回]"
        click.echo(f"  {bid.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                   f"{buyer.name if buyer else bid.buyer_id}: "
                   f"{format_decimal(bid.amount)} 元{status}")
    click.echo("")
    
    click.echo("[EXCL] 被排除的出价:")
    if not settlement.excluded_bids:
        click.echo("  无")
    else:
        for excl in settlement.excluded_bids:
            buyer = buyer_map.get(excl.bid.buyer_id)
            click.echo(f"  - {excl.bid.bid_id}: {format_decimal(excl.bid.amount)} 元 "
                       f"({buyer.name if buyer else excl.bid.buyer_id})")
            click.echo(f"    原因: {excl.reason}")
            click.echo(f"    规则: {excl.rule}")
    click.echo("")
    
    click.echo("[RESULT] 成交结果:")
    for line in settlement.explanation:
        click.echo(f"  {line}")
    click.echo("")
    
    if settlement.fees:
        click.echo("[FEE] 费用拆分:")
        for fee_name, fee_amount in settlement.fees.items():
            click.echo(f"  {fee_name}: {format_decimal(fee_amount)} 元")
        click.echo("")
    
    if settlement.disputes:
        click.echo("[DISPUTE] 关联争议:")
        for disp in settlement.disputes:
            click.echo(f"  - {disp.dispute_id}: {disp.type.value} - {disp.description}")
            click.echo(f"    状态: {disp.status.value}")
            if disp.resolution_notes:
                click.echo(f"    处理备注: {disp.resolution_notes}")
        click.echo("")
    
    if settlement.audit_flags:
        click.echo("[AUDIT] 审计标记:")
        for flag in settlement.audit_flags:
            click.echo(f"  - {flag}")


@main.command()
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]), default="json", help="导出格式")
@click.option("--output", type=click.Path(), help="输出目录或文件路径")
@click.option("--include", multiple=True, default=["all"], help="包含的内容类型: settlements, buyers, sellers, audit")
@click.pass_context
def export(ctx: click.Context, output_format: str, output: str, include: List[str]) -> None:
    """导出汇总报表"""
    data = load_data_with_default(ctx.obj["data_dir"])
    
    click.echo("正在生成汇总报表...")
    click.echo("")
    
    settlements, audit_findings = process_batch_settlement(
        "BATCH-001",
        data["lots"],
        data["bids"],
        data["buyers"],
        data["sellers"],
        data["disputes"],
        data["fee_rules"]
    )
    
    buyer_bills = []
    for buyer in data["buyers"]:
        bill = calculate_buyer_bill(buyer, settlements, data["fee_rules"])
        if bill.settlements or bill.penalties > 0:
            buyer_bills.append(bill)
    
    seller_statements = []
    for seller in data["sellers"]:
        stmt = calculate_seller_statement(seller, settlements, data["fee_rules"])
        seller_statements.append(stmt)
    
    include_all = "all" in include
    
    if output_format == "json":
        export_data = {}
        if include_all or "settlements" in include:
            export_data["settlements"] = [s.to_dict() for s in settlements]
        if include_all or "buyers" in include:
            export_data["buyer_bills"] = [b.to_dict() for b in buyer_bills]
        if include_all or "sellers" in include:
            export_data["seller_statements"] = [s.to_dict() for s in seller_statements]
        if include_all or "audit" in include:
            export_data["audit_findings"] = audit_findings
        
        output_path = output or "auction_summary.json"
        save_json_file(output_path, export_data)
        click.echo(f"[OK] 汇总报表已导出到: {output_path}")
        
        total_sales = sum(
            (s.sale_price or Decimal("0")) for s in settlements if s.is_sold
        )
        click.echo("")
        click.echo("导出内容:")
        if include_all or "settlements" in include:
            click.echo(f"  - {len(settlements)} 条拍品结算记录")
        if include_all or "buyers" in include:
            click.echo(f"  - {len(buyer_bills)} 份买家账单")
        if include_all or "sellers" in include:
            click.echo(f"  - {len(seller_statements)} 份卖家结算单")
        if include_all or "audit" in include:
            click.echo(f"  - {len(audit_findings)} 项审计发现")
        click.echo(f"总成交额: {format_decimal(total_sales)} 元")
        return
    
    if output_format == "csv":
        output_dir = output or "auction_exports"
        os.makedirs(output_dir, exist_ok=True)
        
        files_created = []
        if include_all or "settlements" in include:
            path = os.path.join(output_dir, "settlements.csv")
            export_settlements_to_csv(settlements, path)
            files_created.append(path)
        if include_all or "buyers" in include:
            path = os.path.join(output_dir, "buyer_bills.csv")
            export_buyer_bills_to_csv(buyer_bills, path)
            files_created.append(path)
        if include_all or "sellers" in include:
            path = os.path.join(output_dir, "seller_statements.csv")
            export_seller_statements_to_csv(seller_statements, path)
            files_created.append(path)
        if include_all or "audit" in include:
            path = os.path.join(output_dir, "audit_findings.csv")
            export_audit_findings_to_csv(audit_findings, path)
            files_created.append(path)
        
        click.echo(f"[OK] CSV文件已导出到目录: {output_dir}")
        click.echo("")
        for f in files_created:
            click.echo(f"  - {os.path.basename(f)}")


if __name__ == "__main__":
    main()
