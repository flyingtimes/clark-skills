#!/usr/bin/env python3
"""
使用物化视图 mv_logic_element_device_room_station 查询RRU序列号和PL规划点编号
基于物化视图的简化查询，相比传统多表连接性能更好
"""

import argparse
import sys
import json
from db_config import config

def find_rru_planning_mv(serial_number=None, planning_code=None, city=None, 
                         rru_id=None, limit=100, mock_mode=False):
    """
    使用物化视图查询RRU序列号和规划点信息
    
    Args:
        serial_number: RRU序列号过滤（模糊匹配）
        planning_code: 规划点编码过滤
        city: 城市过滤
        rru_id: RRU ID精确过滤
        limit: 返回结果数量限制
        mock_mode: 是否使用模拟数据模式
    
    Returns:
        查询结果字典
    """
    if mock_mode:
        return _get_mock_data(serial_number, planning_code, city, rru_id, limit)
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("错误: psycopg2未安装。请安装: pip install psycopg2-binary")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(**config.psycopg2_params())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 构建WHERE条件
        where_conditions = []
        params = []
        
        # 筛选RRU设备（根据device_uuid前缀或device_type）
        where_conditions.append("(mv.device_uuid LIKE 'RRU-%' OR mv.device_uuid LIKE 'AAU-%')")
        
        if rru_id:
            where_conditions.append("mv.device_uuid = %s")
            params.append(rru_id)
        
        if serial_number:
            # 需要关联wr_device_rru表获取SN
            # 先构建基础查询
            pass
        
        if planning_code:
            where_conditions.append("pcp.plan_code ILIKE %s")
            params.append(f"%{planning_code}%")
        
        if city:
            where_conditions.append("mv.city ILIKE %s")
            params.append(f"%{city}%")
        
        # 排除已删除记录
        where_conditions.append("mv.device_uuid IS NOT NULL")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # 基于物化视图的查询
        # 版本1：假设device_planid直接关联规划点表
        query_v1 = f"""
            SELECT 
                mv.device_uuid AS rru_id,
                mv.device_name AS rru_name,
                rru.serial_number AS rru_sn,
                pcp.site_planning_code AS planning_point_code,
                pcp.site_planning_name AS planning_point_name,
                mv.element_id AS associated_element_id,
                mv.element_name AS associated_element_name,
                mv.net_type AS network_type,
                mv.element_type AS element_type,
                mv.room_name,
                mv.station_name,
                mv.city,
                mv.longitude,
                mv.latitude,
                mv.life_cycle_status,
                mv.use_time,
                mv.setup_time,
                mv.is_virtual_room,
                mv.tower_add_code,
                mv.station_cuid,
                mv.room_cuid,
                mv.element_planid,
                mv.device_planid,
                pcp.band,
                pcp.station_type,
                pcp.cover_type
            FROM npas.mv_logic_element_device_room_station mv
            LEFT JOIN npas.wr_device_rru rru ON mv.device_uuid = rru.rru_id
            LEFT JOIN npas.pl_cover_point pcp ON mv.device_planid = pcp.site_planning_id
            {where_clause}
            ORDER BY mv.city, mv.station_name, rru.serial_number
            LIMIT %s;
        """
        
        # 版本2：使用传统规划点关联链（如果版本1不返回数据）
        query_v2 = f"""
            SELECT 
                mv.device_uuid AS rru_id,
                mv.device_name AS rru_name,
                rru.serial_number AS rru_sn,
                pcp.site_planning_code AS planning_point_code,
                pcp.site_planning_name AS planning_point_name,
                mv.element_id AS associated_element_id,
                mv.element_name AS associated_element_name,
                mv.net_type AS network_type,
                mv.element_type AS element_type,
                mv.room_name,
                mv.station_name,
                mv.city,
                mv.longitude,
                mv.latitude,
                mv.life_cycle_status,
                mv.use_time,
                mv.setup_time,
                mv.is_virtual_room,
                mv.tower_add_code,
                mv.station_cuid,
                mv.room_cuid,
                mv.element_planid,
                mv.device_planid,
                pcp.band,
                pcp.station_type,
                pcp.cover_type
            FROM npas.mv_logic_element_device_room_station mv
            LEFT JOIN npas.wr_device_rru rru ON mv.device_uuid = rru.rru_id
            -- 传统规划点关联链
            LEFT JOIN npas.ac_access_batch_rel_rs aabrr ON mv.element_id = aabrr.rs_cuid::text
            LEFT JOIN npas.ac_access_batch aab ON aabrr.access_batch_id = aab.access_batch_id
            LEFT JOIN npas.ac_access_solution aas ON aab.access_solution_id = aas.access_solution_id
            LEFT JOIN npas.pl_cover_point pcp ON aas.site_planning_id = pcp.site_planning_id
            {where_clause}
            ORDER BY mv.city, mv.station_name, rru.serial_number
            LIMIT %s;
        """
        
        params.append(limit)
        
        # 尝试版本1查询
        try:
            cursor.execute(query_v1, params)
            results = cursor.fetchall()
            
            # 如果版本1没有结果，尝试版本2
            if not results and where_clause:  # 有过滤条件但无结果，可能关联方式不同
                cursor.execute(query_v2, params)
                results = cursor.fetchall()
        except Exception as e:
            # 如果版本1出错，尝试版本2
            print(f"版本1查询出错，尝试版本2: {e}", file=sys.stderr)
            cursor.execute(query_v2, params)
            results = cursor.fetchall()
        
        # 获取统计信息
        summary_query = """
            SELECT 
                COUNT(DISTINCT mv.device_uuid) as total_devices,
                COUNT(DISTINCT CASE WHEN mv.device_uuid LIKE 'RRU-%' THEN mv.device_uuid END) as total_rrus,
                COUNT(DISTINCT CASE WHEN mv.device_uuid LIKE 'AAU-%' THEN mv.device_uuid END) as total_aaus,
                COUNT(DISTINCT pcp.site_planning_id) as unique_planning_points,
                ROUND(100.0 * COUNT(DISTINCT CASE WHEN pcp.site_planning_id IS NOT NULL THEN mv.device_uuid END) / 
                      COUNT(DISTINCT mv.device_uuid), 2) as planning_coverage_rate
            FROM npas.mv_logic_element_device_room_station mv
            LEFT JOIN npas.pl_cover_point pcp ON mv.device_planid = pcp.site_planning_id
            WHERE mv.device_uuid LIKE 'RRU-%' OR mv.device_uuid LIKE 'AAU-%';
        """
        
        cursor.execute(summary_query)
        summary = cursor.fetchone()
        
        # 按序列号过滤（如果在查询后需要过滤）
        if serial_number and results:
            filtered_results = []
            for r in results:
                if serial_number.lower() in str(r.get('rru_sn', '')).lower():
                    filtered_results.append(r)
            results = filtered_results
        
        cursor.close()
        conn.close()
        
        return {
            "query_method": "materialized_view",
            "results": results,
            "summary": summary,
            "result_count": len(results)
        }
        
    except Exception as e:
        print(f"数据库错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n切换到模拟数据模式...")
        return _get_mock_data(serial_number, planning_code, city, rru_id, limit)

def _get_mock_data(serial_number=None, planning_code=None, city=None, rru_id=None, limit=10):
    """生成模拟数据用于测试"""
    import random
    from datetime import datetime, timedelta
    
    mock_results = []
    
    # 模拟数据
    planning_points = [
        {"code": "PLAN-001", "name": "城市中心5G扩容", "band": "2.6GHz"},
        {"code": "PLAN-002", "name": "工业园区覆盖", "band": "1.8GHz"},
        {"code": "PLAN-003", "name": "地铁线路覆盖", "band": "700MHz"},
    ]
    
    cities = ["上海", "北京", "广州", "深圳", "成都"]
    stations = ["中心站", "边际站", "室内站", "微站"]
    
    for i in range(min(limit, 15)):
        planning = random.choice(planning_points + [None])
        
        record = {
            "rru_id": f"RRU-{1000 + i:04d}",
            "rru_name": f"RRU设备_{i+1}",
            "rru_sn": f"SN_{2024000 + i}",
            "planning_point_code": planning["code"] if planning else None,
            "planning_point_name": planning["name"] if planning else None,
            "associated_element_id": f"CELL-{5000 + i}",
            "associated_element_name": f"小区_{i+1}",
            "network_type": random.choice(["4G", "5G"]),
            "element_type": random.choice(["eutrancell", "nrcell"]),
            "room_name": f"机房_{random.choice(['A', 'B', 'C'])}",
            "station_name": f"{random.choice(cities)}{random.choice(stations)}",
            "city": random.choice(cities),
            "longitude": round(120 + random.random(), 6),
            "latitude": round(30 + random.random(), 6),
            "life_cycle_status": random.choice(["现网有业务", "预分配", "退网"]),
            "use_time": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            "setup_time": (datetime.now() - timedelta(days=random.randint(1, 730))).isoformat(),
            "is_virtual_room": random.choice(["是", "否"]),
            "tower_add_code": f"TOWER-{100 + i}",
            "band": planning["band"] if planning else None,
            "station_type": random.choice(["宏站", "室分", "微站"]),
            "cover_type": random.choice(["室外覆盖", "室内覆盖"]),
        }
        
        # 应用过滤条件
        skip = False
        if serial_number and serial_number not in record["rru_sn"]:
            skip = True
        if planning_code and planning_code not in str(record["planning_point_code"]):
            skip = True
        if city and city not in record["city"]:
            skip = True
        if rru_id and rru_id != record["rru_id"]:
            skip = True
        
        if not skip:
            mock_results.append(record)
    
    summary = {
        "total_devices": 150,
        "total_rrus": 120,
        "total_aaus": 30,
        "unique_planning_points": 3,
        "planning_coverage_rate": 75.5
    }
    
    return {
        "query_method": "mock_data",
        "results": mock_results[:limit],
        "summary": summary,
        "result_count": len(mock_results[:limit])
    }

def format_results(rru_data, output_format="text"):
    """格式化输出结果"""
    if output_format == "json":
        return json.dumps(rru_data, indent=2, ensure_ascii=False)
    
    output = []
    results = rru_data.get("results", [])
    summary = rru_data.get("summary", {})
    query_method = rru_data.get("query_method", "unknown")
    
    output.append("=" * 80)
    output.append("RRU序列号与PL规划点编号查询（基于物化视图）")
    output.append(f"查询方法: {query_method}")
    output.append("=" * 80)
    output.append("")
    
    # 统计信息
    output.append("统计概览")
    output.append("-" * 40)
    output.append(f"设备总数: {summary.get('total_devices', 0):,}")
    output.append(f"RRU数量: {summary.get('total_rrus', 0):,}")
    output.append(f"AAU数量: {summary.get('total_aaus', 0):,}")
    output.append(f"规划点数量: {summary.get('unique_planning_points', 0):,}")
    output.append(f"规划覆盖率: {summary.get('planning_coverage_rate', 0):.2f}%")
    output.append("")
    
    # 查询结果
    output.append(f"查询结果 ({rru_data.get('result_count', 0)} 条)")
    output.append("-" * 40)
    
    if not results:
        output.append("没有找到匹配的记录")
        output.append("可能原因:")
        output.append("1. 物化视图未刷新（使用 REFRESH MATERIALIZED VIEW）")
        output.append("2. 数据库字段名称与脚本假设不同")
        output.append("3. 没有符合条件的RRU记录")
    else:
        for i, rru in enumerate(results, 1):
            output.append(f"\n{i}. RRU ID: {rru.get('rru_id', 'N/A')}")
            output.append(f"   序列号: {rru.get('rru_sn', 'N/A')}")
            output.append(f"   设备名称: {rru.get('rru_name', 'N/A')}")
            output.append(f"   状态: {rru.get('life_cycle_status', 'N/A')}")
            
            # 规划点信息
            if rru.get('planning_point_code'):
                output.append(f"   规划点: {rru.get('planning_point_code')} - {rru.get('planning_point_name', '')}")
                output.append(f"   频段: {rru.get('band', 'N/A')}")
                output.append(f"   站型: {rru.get('station_type', 'N/A')}")
                output.append(f"   覆盖类型: {rru.get('cover_type', 'N/A')}")
            else:
                output.append(f"   规划点: 未关联")
            
            # 位置信息
            output.append(f"   位置: {rru.get('room_name', 'N/A')} → {rru.get('station_name', 'N/A')}")
            output.append(f"   城市: {rru.get('city', 'N/A')}")
            output.append(f"   坐标: {rru.get('latitude', 'N/A')}, {rru.get('longitude', 'N/A')}")
            
            # 关联元素
            output.append(f"   关联元素: {rru.get('associated_element_id', 'N/A')} ({rru.get('element_type', 'N/A')})")
            output.append(f"   网络类型: {rru.get('network_type', 'N/A')}")
            
            # 虚拟机房
            if rru.get('is_virtual_room'):
                output.append(f"   虚拟机房: {rru.get('is_virtual_room')}")
    
    output.append("")
    output.append("字段说明")
    output.append("-" * 40)
    output.append("  rru_sn: RRU序列号 (Serial Number)")
    output.append("  planning_point_code: PL规划点编号")
    output.append("  planning_point_name: 规划点名称")
    output.append("  associated_element_id: 关联的逻辑元素ID（小区/基站）")
    output.append("  network_type: 网络类型（2G/4G/5G）")
    output.append("  element_type: 元素类型（eutrancell/gsmcell/nrcell/enb/gnb）")
    output.append("  station_cuid/room_cuid: 站点/机房同步ID（用于跨系统集成）")
    
    output.append("")
    output.append("物化视图优势")
    output.append("-" * 40)
    output.append("1. 查询简化: 将复杂的多表连接简化为单表查询")
    output.append("2. 性能优化: 预计算关联，查询速度更快")
    output.append("3. 数据完整: 包含无设备关联的记录，数据更全面")
    output.append("4. 字段丰富: 包含规划信息、同步ID、虚拟机房标识等")
    
    output.append("")
    output.append("使用建议")
    output.append("-" * 40)
    output.append("1. 定期刷新物化视图: REFRESH MATERIALIZED VIEW npas.mv_logic_element_device_room_station")
    output.append("2. 创建索引: 在 element_id, device_uuid, room_id, station_id 等字段上创建索引")
    output.append("3. 优先使用: 对于涉及多种资源关联的查询，优先使用此视图")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(
        description="使用物化视图查询RRU序列号和PL规划点编号",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --serial "SN2024"                    # 按序列号查询
  %(prog)s --planning-code "PLAN-001"           # 按规划点编码查询
  %(prog)s --city "上海" --limit 20             # 按城市查询，限制20条
  %(prog)s --rru-id "RRU-1001"                  # 按RRU ID精确查询
  %(prog)s --mock                               # 使用模拟数据模式
  %(prog)s --json                               # JSON格式输出
        """
    )
    
    parser.add_argument("--serial", help="按RRU序列号过滤（模糊匹配）")
    parser.add_argument("--planning-code", help="按规划点编码过滤")
    parser.add_argument("--city", help="按城市过滤")
    parser.add_argument("--rru-id", help="按RRU ID精确过滤")
    parser.add_argument("--limit", type=int, default=100, help="返回结果数量限制（默认: 100）")
    parser.add_argument("--mock", action="store_true", help="使用模拟数据模式")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    args = parser.parse_args()
    
    # 检查是否提供了过滤条件
    if not any([args.serial, args.planning_code, args.city, args.rru_id]) and args.limit > 500:
        print("警告: 无过滤条件的大规模查询可能影响性能。", file=sys.stderr)
        confirm = input("继续? (y/n): ")
        if confirm.lower() != 'y':
            return
    
    # 查询数据
    rru_data = find_rru_planning_mv(
        serial_number=args.serial,
        planning_code=args.planning_code,
        city=args.city,
        rru_id=args.rru_id,
        limit=args.limit,
        mock_mode=args.mock
    )
    
    # 输出结果
    output_format = "json" if args.json else "text"
    print(format_results(rru_data, output_format))

if __name__ == "__main__":
    main()