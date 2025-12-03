"""
数据管理器
负责统一管理所有学院的教师数据，包括数据合并、去重、统计等功能
"""
import json
import csv
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class TeacherDataManager:
    """教师数据管理器"""
    
    def __init__(self, data_dir='data'):
        """
        初始化数据管理器
        
        Args:
            data_dir (str): 数据根目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'
        self.colleges_dir = self.data_dir / 'colleges'
        self.reports_dir = self.data_dir / 'reports'
        self.backup_dir = self.data_dir / 'backup'
        
        # 确保所有目录存在
        for directory in [self.raw_dir, self.processed_dir, self.colleges_dir, 
                         self.reports_dir, self.backup_dir]:
            directory.mkdir(exist_ok=True)
            
        # 创建处理后数据的子目录
        (self.processed_dir / 'merged').mkdir(exist_ok=True)
        (self.processed_dir / 'filtered').mkdir(exist_ok=True)
        (self.processed_dir / 'exported').mkdir(exist_ok=True)
        
        # 创建报告的子目录
        (self.reports_dir / 'statistics').mkdir(exist_ok=True)
        (self.reports_dir / 'quality').mkdir(exist_ok=True)
        (self.reports_dir / 'analysis').mkdir(exist_ok=True)
        
        # 统一的字段映射
        self.standard_fields = {
            'name': '姓名',
            'college': '学院',
            'contact_info': '联系方式',
            'office_location': '办公地点',
            'research_direction': '研究方向',
            'supervisor_type': '导师类型',
            'personal_introduction': '个人简介',
            'courses_taught': '主讲课程',
            'research_projects': '研究项目',
            'student_guidance': '指导学生',
            'education': '教育背景',
            'experience': '工作经历',
            'honors': '荣誉奖励',
            'publications': '发表论文',
            'url': '详情链接',
            'created_at': '采集时间'
        }
    

    

    
    def save_raw_data(self, teachers_data, college_code, college_name):
        """
        保存原始数据到raw目录
        
        Args:
            teachers_data (list): 教师数据列表
            college_code (str): 学院代码
            college_name (str): 学院名称
        """
        if not teachers_data:
            return
            
        # 创建学院特定的目录
        college_raw_dir = self.raw_dir / college_code
        college_raw_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存JSON格式
        json_filename = f"{college_code}_raw_{timestamp}.json"
        self._save_to_json(teachers_data, college_raw_dir / json_filename)
        
        # 保存CSV格式
        csv_filename = f"{college_code}_raw_{timestamp}.csv"
        self._save_to_csv(teachers_data, college_raw_dir / csv_filename)
        
        logger.info(f"{college_name} 原始数据已保存到 {college_raw_dir}")
    
    def save_college_data(self, teachers_data, college_name):
        """
        保存学院分类数据到colleges目录
        
        Args:
            teachers_data (list): 教师数据列表
            college_name (str): 学院名称
        """
        if not teachers_data:
            return
            
        # 保存完整数据文件
        json_filename = f"{college_name}_teachers.json"
        self._save_to_json(teachers_data, self.colleges_dir / json_filename)
        
        # 保存CSV格式
        csv_filename = f"{college_name}_teachers.csv"
        self._save_to_csv(teachers_data, self.colleges_dir / csv_filename)
    

    
    def _create_backup(self, data, filename_prefix, timestamp):
        """
        创建数据备份
        
        Args:
            data (list): 数据列表
            filename_prefix (str): 文件名前缀
            timestamp (str): 时间戳
        """
        try:
            # 创建日备份目录
            daily_backup_dir = self.backup_dir / 'daily'
            daily_backup_dir.mkdir(exist_ok=True)
            
            # 保存备份
            backup_filename = f"{filename_prefix}_{timestamp}.json"
            self._save_to_json(data, daily_backup_dir / backup_filename)
            
            # 检查是否需要创建周备份和月备份
            current_date = datetime.now()
            
            # 周备份（周一创建）
            if current_date.weekday() == 0:  # 0表示周一
                weekly_backup_dir = self.backup_dir / 'weekly'
                weekly_backup_dir.mkdir(exist_ok=True)
                week_filename = f"{filename_prefix}_week_{current_date.strftime('%Y%W')}.json"
                self._save_to_json(data, weekly_backup_dir / week_filename)
            
            # 月备份（每月1号创建）
            if current_date.day == 1:
                monthly_backup_dir = self.backup_dir / 'monthly'
                monthly_backup_dir.mkdir(exist_ok=True)
                month_filename = f"{filename_prefix}_month_{current_date.strftime('%Y%m')}.json"
                self._save_to_json(data, monthly_backup_dir / month_filename)
                
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
    
    def _save_to_json(self, data, filepath):
        """保存为JSON格式"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON数据已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def _save_to_csv(self, data, filepath):
        """保存为CSV格式"""
        try:
            if not data:
                return
                
            fieldnames = list(data[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for record in data:
                    writer.writerow(record)
            logger.info(f"CSV数据已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def _save_to_excel(self, data, filepath):
        """保存为Excel格式"""
        try:
            if not data:
                return
                
            df = pd.DataFrame(data)
            
            # 重命名列为中文
            chinese_columns = {field: chinese for field, chinese in self.standard_fields.items() if field in df.columns}
            df = df.rename(columns=chinese_columns)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 主数据表
                df.to_excel(writer, sheet_name='教师信息', index=False)
                
                # 按学院分组的统计表
                if '学院' in df.columns:
                    college_stats = df.groupby('学院').size().reset_index(name='教师数量')
                    college_stats.to_excel(writer, sheet_name='学院统计', index=False)
            
            logger.info(f"Excel数据已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            # 如果pandas不可用，退化到CSV
            logger.info("使用CSV格式保存")
            csv_path = str(filepath).replace('.xlsx', '.csv')
            self._save_to_csv(data, csv_path)
    
    def _generate_statistics_report(self, data, filename):
        """生成统计报告"""
        try:
            stats = {
                'total_teachers': len(data),
                'colleges': {},
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_quality': self._analyze_data_quality(data)
            }
            
            # 按学院统计
            for teacher in data:
                college = teacher.get('college', '未知学院')
                if college not in stats['colleges']:
                    stats['colleges'][college] = {
                        'count': 0,
                        'has_contact': 0,
                        'has_research_direction': 0,
                        'has_introduction': 0
                    }
                
                stats['colleges'][college]['count'] += 1
                
                if teacher.get('contact_info'):
                    stats['colleges'][college]['has_contact'] += 1
                if teacher.get('research_direction'):
                    stats['colleges'][college]['has_research_direction'] += 1
                if teacher.get('personal_introduction'):
                    stats['colleges'][college]['has_introduction'] += 1
            
            # 保存统计报告到reports目录
            stats_dir = self.reports_dir / 'statistics'
            filepath = stats_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            logger.info(f"统计报告已保存到: {filepath}")
            
            # 同时生成数据质量报告
            self._generate_quality_report(data)
            
        except Exception as e:
            logger.error(f"生成统计报告失败: {e}")
    
    def _generate_quality_report(self, data):
        """生成数据质量报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quality_stats = {
                'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_records': len(data),
                'field_completeness': {},
                'duplicate_analysis': {},
                'data_issues': []
            }
            
            if not data:
                return
            # 字段完整性分析
            total = len(data)
            for field in self.standard_fields.keys():
                filled = sum(1 for teacher in data if teacher.get(field, '').strip())
                quality_stats['field_completeness'][field] = {
                    'filled_count': filled,
                    'filled_percentage': round((filled / total) * 100, 2),
                    'empty_count': total - filled
                }
            
            # 重复数据分析
            names = [teacher.get('name', '') for teacher in data if teacher.get('name', '')]
            name_counts = {}
            for name in names:
                name_counts[name] = name_counts.get(name, 0) + 1
            
            duplicates = {name: count for name, count in name_counts.items() if count > 1}
            quality_stats['duplicate_analysis'] = {
                'duplicate_names': duplicates,
                'duplicate_count': len(duplicates),
                'total_duplicates': sum(duplicates.values()) - len(duplicates)
            }
            
            # 数据质量问题检查
            for i, teacher in enumerate(data):
                issues = []
                if not teacher.get('name', '').strip():
                    issues.append('缺少姓名')
                if not teacher.get('college', '').strip():
                    issues.append('缺少学院信息')
                if not teacher.get('contact_info', '').strip():
                    issues.append('缺少联系方式')
                
                if issues:
                    quality_stats['data_issues'].append({
                        'record_index': i,
                        'teacher_name': teacher.get('name', '未知'),
                        'issues': issues
                    })
            
            # 保存质量报告
            quality_dir = self.reports_dir / 'quality'
            quality_filename = f"quality_report_{timestamp}.json"
            filepath = quality_dir / quality_filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(quality_stats, f, ensure_ascii=False, indent=2)
            logger.info(f"数据质量报告已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"生成数据质量报告失败: {e}")
    
    def _analyze_data_quality(self, data):
        """分析数据质量"""
        if not data:
            return {}
        
        total = len(data)
        quality_stats = {}
        
        for field in ['name', 'contact_info', 'research_direction', 'personal_introduction']:
            filled = sum(1 for teacher in data if teacher.get(field, '').strip())
            quality_stats[field] = {
                'filled_count': filled,
                'filled_percentage': round((filled / total) * 100, 2)
            }
        
        return quality_stats
    
    def load_existing_data(self, filepath):
        """
        加载已有的数据文件
        
        Args:
            filepath (str): 数据文件路径
            
        Returns:
            list: 教师数据列表
        """
        try:
            filepath = Path(filepath)
            
            if filepath.suffix == '.json':
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif filepath.suffix == '.csv':
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            else:
                logger.error(f"不支持的文件格式: {filepath.suffix}")
                return []
                
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            return []