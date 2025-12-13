"""
表格合并工具
用于合并所有学院的教师数据到一个文件
"""
import json
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TableMerger:
    """表格合并工具类"""
    
    def __init__(self, data_dir='data/colleges'):
        """
        初始化合并工具
        
        Args:
            data_dir (str): 学院数据目录
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path('data/processed/merged')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_json_files(self):
        """加载所有JSON文件"""
        all_data = []
        json_files = list(self.data_dir.glob('*_teachers.json'))
        
        logger.info(f"找到 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # 为每条记录添加来源学院
                        college_name = json_file.stem.replace('_teachers', '')
                        for teacher in data:
                            if 'college' not in teacher or not teacher['college']:
                                teacher['college'] = college_name
                        all_data.extend(data)
                        logger.info(f"从 {json_file.name} 加载了 {len(data)} 条记录")
                    else:
                        logger.warning(f"{json_file.name} 不是列表格式")
            except Exception as e:
                logger.error(f"读取 {json_file.name} 失败: {e}")
        
        logger.info(f"总共加载了 {len(all_data)} 条记录")
        return all_data
    
    def load_csv_files(self):
        """加载所有CSV文件"""
        all_dataframes = []
        csv_files = list(self.data_dir.glob('*_teachers.csv'))
        
        logger.info(f"找到 {len(csv_files)} 个CSV文件")
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                # 添加来源学院列
                college_name = csv_file.stem.replace('_teachers', '')
                if 'college' not in df.columns or df['college'].isna().all():
                    df['college'] = college_name
                all_dataframes.append(df)
                logger.info(f"从 {csv_file.name} 加载了 {len(df)} 条记录")
            except Exception as e:
                logger.error(f"读取 {csv_file.name} 失败: {e}")
        
        if all_dataframes:
            merged_df = pd.concat(all_dataframes, ignore_index=True)
            logger.info(f"总共加载了 {len(merged_df)} 条记录")
            return merged_df
        else:
            return pd.DataFrame()
    
    def deduplicate(self, data, by='url'):
        """
        去重
        
        Args:
            data: 数据（列表或DataFrame）
            by (str): 去重依据字段，默认为'url'
        
        Returns:
            去重后的数据
        """
        if isinstance(data, list):
            # JSON数据去重
            seen = set()
            unique_data = []
            for teacher in data:
                key = teacher.get(by, '')
                if key and key not in seen:
                    seen.add(key)
                    unique_data.append(teacher)
                elif not key:
                    # 如果没有URL，使用姓名+学院作为key
                    key = f"{teacher.get('name', '')}_{teacher.get('college', '')}"
                    if key not in seen:
                        seen.add(key)
                        unique_data.append(teacher)
            
            logger.info(f"去重前: {len(data)} 条，去重后: {len(unique_data)} 条，删除: {len(data) - len(unique_data)} 条")
            return unique_data
        
        elif isinstance(data, pd.DataFrame):
            # DataFrame去重
            original_count = len(data)
            if by in data.columns:
                # 先去除空值，再去重
                data_dedup = data.dropna(subset=[by]).drop_duplicates(subset=[by], keep='first')
                # 添加回没有URL的记录（如果它们的姓名+学院组合是唯一的）
                no_url = data[data[by].isna()]
                if len(no_url) > 0:
                    no_url_dedup = no_url.drop_duplicates(subset=['name', 'college'], keep='first')
                    data_dedup = pd.concat([data_dedup, no_url_dedup], ignore_index=True)
            else:
                data_dedup = data.drop_duplicates(subset=['name', 'college'], keep='first')
            
            logger.info(f"去重前: {original_count} 条，去重后: {len(data_dedup)} 条，删除: {original_count - len(data_dedup)} 条")
            return data_dedup
        
        return data
    
    def merge_and_save_json(self, output_filename=None, deduplicate=True):
        """
        合并所有JSON文件并保存
        
        Args:
            output_filename (str): 输出文件名，默认自动生成
            deduplicate (bool): 是否去重
        
        Returns:
            str: 输出文件路径
        """
        # 加载数据
        all_data = self.load_json_files()
        
        if not all_data:
            logger.warning("没有数据可以合并")
            return None
        
        # 去重
        if deduplicate:
            all_data = self.deduplicate(all_data, by='url')
        
        # 生成输出文件名
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'all_teachers_merged_{timestamp}.json'
        
        output_path = self.output_dir / output_filename
        
        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 合并完成，保存到: {output_path}")
        logger.info(f"  总记录数: {len(all_data)}")
        
        return str(output_path)
    
    def merge_and_save_csv(self, output_filename=None, deduplicate=True):
        """
        合并所有CSV文件并保存
        
        Args:
            output_filename (str): 输出文件名，默认自动生成
            deduplicate (bool): 是否去重
        
        Returns:
            str: 输出文件路径
        """
        # 加载数据
        merged_df = self.load_csv_files()
        
        if merged_df.empty:
            logger.warning("没有数据可以合并")
            return None
        
        # 去重
        if deduplicate:
            merged_df = self.deduplicate(merged_df, by='url')
        
        # 生成输出文件名
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'all_teachers_merged_{timestamp}.csv'
        
        output_path = self.output_dir / output_filename
        
        # 保存
        merged_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"✓ 合并完成，保存到: {output_path}")
        logger.info(f"  总记录数: {len(merged_df)}")
        
        return str(output_path)
    
    def merge_and_save_excel(self, output_filename=None, deduplicate=True):
        """
        合并所有数据并保存为Excel文件
        
        Args:
            output_filename (str): 输出文件名，默认自动生成
            deduplicate (bool): 是否去重
        
        Returns:
            str: 输出文件路径
        """
        # 加载数据
        merged_df = self.load_csv_files()
        
        if merged_df.empty:
            logger.warning("没有数据可以合并")
            return None
        
        # 去重
        if deduplicate:
            merged_df = self.deduplicate(merged_df, by='url')
        
        # 生成输出文件名
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'all_teachers_merged_{timestamp}.xlsx'
        
        output_path = self.output_dir / output_filename
        
        # 保存为Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            merged_df.to_excel(writer, sheet_name='全部教师', index=False)
            
            # 按学院分组统计
            college_stats = merged_df['college'].value_counts().reset_index()
            college_stats.columns = ['学院', '教师数量']
            college_stats.to_excel(writer, sheet_name='学院统计', index=False)
        
        logger.info(f"✓ 合并完成，保存到: {output_path}")
        logger.info(f"  总记录数: {len(merged_df)}")
        logger.info(f"  包含学院数: {merged_df['college'].nunique()}")
        
        return str(output_path)
    
    def merge_all_formats(self, base_filename=None, deduplicate=True):
        """
        一次性生成所有格式的合并文件
        
        Args:
            base_filename (str): 基础文件名（不含扩展名），默认自动生成
            deduplicate (bool): 是否去重
        
        Returns:
            dict: 包含所有输出文件路径的字典
        """
        if base_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f'all_teachers_merged_{timestamp}'
        
        results = {}
        
        # 生成JSON
        logger.info("=" * 60)
        logger.info("开始生成JSON格式...")
        json_file = self.merge_and_save_json(f'{base_filename}.json', deduplicate)
        if json_file:
            results['json'] = json_file
        
        # 生成CSV
        logger.info("=" * 60)
        logger.info("开始生成CSV格式...")
        csv_file = self.merge_and_save_csv(f'{base_filename}.csv', deduplicate)
        if csv_file:
            results['csv'] = csv_file
        
        # 生成Excel
        logger.info("=" * 60)
        logger.info("开始生成Excel格式...")
        excel_file = self.merge_and_save_excel(f'{base_filename}.xlsx', deduplicate)
        if excel_file:
            results['excel'] = excel_file
        
        logger.info("=" * 60)
        logger.info("✓ 所有格式合并完成！")
        logger.info(f"  输出目录: {self.output_dir}")
        for format_name, file_path in results.items():
            logger.info(f"  - {format_name.upper()}: {Path(file_path).name}")
        
        return results
    
    def get_statistics(self):
        """获取统计信息"""
        merged_df = self.load_csv_files()
        
        if merged_df.empty:
            logger.warning("没有数据")
            return None
        
        stats = {
            '总记录数': len(merged_df),
            '学院数量': merged_df['college'].nunique(),
            '各学院教师数量': merged_df['college'].value_counts().to_dict(),
            '有邮箱的教师': merged_df['contact_info'].notna().sum(),
            '有职称的教师': merged_df['supervisor_type'].notna().sum(),
        }
        
        logger.info("=" * 60)
        logger.info("数据统计:")
        logger.info(f"  总记录数: {stats['总记录数']}")
        logger.info(f"  学院数量: {stats['学院数量']}")
        logger.info(f"  有邮箱: {stats['有邮箱的教师']}")
        logger.info(f"  有职称: {stats['有职称的教师']}")
        logger.info("\n各学院教师数量:")
        for college, count in sorted(stats['各学院教师数量'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {college}: {count}")
        
        return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='教师数据表格合并工具')
    parser.add_argument('--format', choices=['json', 'csv', 'excel', 'all'], default='all',
                       help='输出格式 (默认: all - 所有格式)')
    parser.add_argument('--output', type=str, help='输出文件名（不含扩展名）')
    parser.add_argument('--no-dedup', action='store_true', help='不进行去重')
    parser.add_argument('--stats', action='store_true', help='只显示统计信息')
    parser.add_argument('--data-dir', type=str, default='data/colleges',
                       help='数据目录 (默认: data/colleges)')
    
    args = parser.parse_args()
    
    # 创建合并工具
    merger = TableMerger(data_dir=args.data_dir)
    
    # 如果只显示统计信息
    if args.stats:
        merger.get_statistics()
        return
    
    # 执行合并
    deduplicate = not args.no_dedup
    
    if args.format == 'json':
        merger.merge_and_save_json(args.output, deduplicate)
    elif args.format == 'csv':
        merger.merge_and_save_csv(args.output, deduplicate)
    elif args.format == 'excel':
        merger.merge_and_save_excel(args.output, deduplicate)
    else:  # all
        merger.merge_all_formats(args.output, deduplicate)


if __name__ == '__main__':
    main()
