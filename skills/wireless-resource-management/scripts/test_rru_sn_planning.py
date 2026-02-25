#!/usr/bin/env python3
"""
测试脚本：查询RRU序列号和PL规划点编号
如果没有实际数据库，这个脚本会生成模拟数据用于测试
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
import random

def generate_mock_data(num_records=10):
    """生成模拟的RRU和规划点数据"""
    mock_results = []
    
    # 模拟的规划点列表
    planning_points = [
        {"id": "PLAN-2023-001", "code": "P001", "name": "城市中心_5G扩容项目", "band": "2.6GHz"},
        {"id": "PLAN-2023-002", "code": "P002", "name": "工业园区覆盖", "band": "1.8GHz"},
        {"id": "PLAN-2023-003", "code": "P003", "name": "地铁线路覆盖", "band": "700MHz"},
        {"id": "PLAN-2023-004", "code": "P004", "name": "高速公路覆盖", "band": "2.1GHz"},
        {"id": "PLAN-2023-005", "code": "P005", "name": "农村区域覆盖", "band": "900MHz"},
    ]
    
    # 模拟的RRU序列号前缀
    sn_prefixes = ["HW", "ZTE", "ERIC", "NOKIA", "SIEMENS"]
    
    for i in range(num_records):
        planning = random.choice(planning_points + [None])  # 有些RRU可能没有规划点
        
        # 生成RRU ID和序列号
        rru_id = f"RRU-{1000 + i:04d}"
        sn_prefix = random.choice(sn_prefixes)
        serial_number = f"{sn_prefix}{2023000 + i}"
        
        # 生成安装日期
        install_date = datetime.now() - timedelta(days=random.randint(1, 365))
        
        record = {
            "rru_id": rru_id,
            "rru_name": f"RRU设备_{i+1}",
            "device_model": f"MODEL-{random.choice(['A', 'B', 'C'])}",
            "serial_number": serial_number,
            "manufacturer": sn_prefix,
            "installation_date": install_date.strftime("%Y-%m-%d"),
            "life_cycle_status": random.choice(["现网有业务", "预分配", "退网", "故障"]),
            "room_name": f"机房_{random.choice(['A', 'B', 'C'])}",
            "station_name": f"站点_{random.choice(['中心站', '边际站', '室内站'])}",
            "cell_count": random.randint(1, 6),
        }
        
        # 添加规划点信息（如果存在）
        if planning:
            record.update({
                "site_planning_id": planning["id"],
                "site_planning_code": planning["code"],
                "site_planning_name": planning["name"],
                "band": planning["band"],
                "station_type": random.choice(["宏站", "室分", "微站"]),
                "cover_type": random.choice(["室外覆盖", "室内覆盖", "特殊场景"]),
                "network_type": random.choice(["5G", "4G", "3G"]),
                "planned_latitude": round(30 + random.random(), 6),
                "planned_longitude": round(120 + random.random(), 6),
                "planned_address": f"模拟地址_{i+1}",
            })
        
        mock_results.append(record)
    
    return mock_results

def query_rru_sn_planning(serial_number=None, planning_id=None, mock_mode=False):
    """
    查询RRU序列号和PL规划点编号
    
    Args:
        serial_number: RRU序列号过滤
        planning_id: 规划点ID过滤
        mock_mode: 是否使用模拟数据模式
    
    Returns:
        查询结果
    """
    if mock_mode:
        # 模拟数据模式
        print("警告：使用模拟数据模式，因为无法连接到实际数据库")
        print("要使用实际数据库，请配置 db_config.py 并设置 mock_mode=False")
        
        all_data = generate_mock_data(20)
        
        # 应用过滤条件
        filtered_data = []
        for record in all_data:
            if serial_number and serial_number not in record.get("serial_number", ""):
                continue
            if planning_id and planning_id != record.get("site_planning_id"):
                continue
            filtered_data.append(record)
        
        summary = {
            "total_rrus": len(all_data),
            "rrus_with_planning": sum(1 for r in all_data if r.get("site_planning_id")),
            "unique_planning_points": len(set(r.get("site_planning_id") for r in all_data if r.get("site_planning_id"))),
            "planning_coverage_rate": round(100.0 * sum(1 for r in all_data if r.get("site_planning_id")) / len(all_data), 2)
        }
        
        return {
            "results": filtered_data,
            "summary": summary
        }
    else:
        # 实际数据库模式 - 使用已有的 find_rru_planning 脚本
        try:
            from find_rru_planning import find_rru_planning
            return find_rru_planning(
                serial_number=serial_number,
                planning_id=planning_id,
                limit=100
            )
        except Exception as e:
            print(f"数据库连接失败: {e}")
            print("切换到模拟数据模式...")
            return query_rru_sn_planning(serial_number, planning_id, mock_mode=True)

def format_results(rru_data, output_format="text"):
    """格式化输出结果"""
    if not rru_data:
        return "没有找到数据"
    
    if output_format == "json":
        return json.dumps(rru_data, indent=2, ensure_ascii=False)
    
    results = rru_data.get("results", [])
    summary = rru_data.get("summary", {})
    
    output = []
    output.append("RRU序列号与PL规划点编号查询结果")
    output.append("=" * 80)
    
    # 统计信息
    output.append("\n统计信息:")
    output.append(f"  RRU总数: {summary.get('total_rrus', 0)}")
    output.append(f"  有规划点的RRU数: {summary.get('rrus_with_planning', 0)}")
    output.append(f"  规划点覆盖率: {summary.get('planning_coverage_rate', 0)}%")
    
    # 详细结果
    if not results:
        output.append("\n没有找到匹配的RRU记录")
    else:
        output.append(f"\n找到 {len(results)} 条RRU记录:")
        output.append("-" * 40)
        
        for i, rru in enumerate(results, 1):
            output.append(f"\n{i}. RRU ID: {rru.get('rru_id', 'N/A')}")
            output.append(f"   序列号(SN): {rru.get('serial_number', 'N/A')}")
            output.append(f"   设备型号: {rru.get('device_model', 'N/A')}")
            output.append(f"   厂商: {rru.get('manufacturer', 'N/A')}")
            output.append(f"   状态: {rru.get('life_cycle_status', 'N/A')}")
            
            # 规划点信息
            if rru.get('site_planning_id'):
                output.append(f"   规划点编号: {rru.get('site_planning_code', 'N/A')}")
                output.append(f"   规划点ID: {rru.get('site_planning_id', 'N/A')}")
                output.append(f"   规划点名称: {rru.get('site_planning_name', 'N/A')}")
                output.append(f"   频段: {rru.get('band', 'N/A')}")
                output.append(f"   网络类型: {rru.get('network_type', 'N/A')}")
            else:
                output.append(f"   规划点: 未关联")
            
            output.append(f"   关联小区数: {rru.get('cell_count', 0)}")
    
    output.append("\n" + "=" * 80)
    output.append("字段说明:")
    output.append("  serial_number: RRU序列号(SN)")
    output.append("  site_planning_code: PL规划点编号")
    output.append("  site_planning_id: PL规划点ID")
    output.append("  site_planning_name: 规划点名称")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="查询RRU序列号和PL规划点编号")
    parser.add_argument("--serial", help="按RRU序列号过滤")
    parser.add_argument("--planning-id", help="按规划点ID过滤")
    parser.add_argument("--planning-code", help="按规划点编号过滤")
    parser.add_argument("--mock", action="store_true", help="使用模拟数据模式")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--limit", type=int, default=20, help="返回结果数量限制")
    
    args = parser.parse_args()
    
    # 查询数据
    rru_data = query_rru_sn_planning(
        serial_number=args.serial,
        planning_id=args.planning_id,
        mock_mode=args.mock
    )
    
    # 输出结果
    output_format = "json" if args.json else "text"
    print(format_results(rru_data, output_format))

if __name__ == "__main__":
    main()