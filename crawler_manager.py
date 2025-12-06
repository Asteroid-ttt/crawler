"""
主控制器
统一管理所有学院的爬取任务，支持并发爬取和数据合并
"""
import logging
import importlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_manager import TeacherDataManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrawlerManager:
    """爬虫管理器"""
    
    def __init__(self, config_path='config/colleges.yaml'):
        """
        初始化管理器
        
        Args:
            config_path (str): 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.data_manager = TeacherDataManager(
            data_dir=self.config.get('global_config', {}).get('data_dir', 'data')
        )
        
        # 爬虫类映射
        self.crawler_classes = {
            'EISTeacherCrawler': 'crawlers.eis_crawler.EISTeacherCrawler',
            'CSTeacherCrawler': 'crawlers.cs_crawler.CSTeacherCrawler',
            'RSGISTeacherCrawler': 'crawlers.rsgis_crawler.RSGISTeacherCrawler',
            'SGGTeacherCrawler': 'crawlers.sgg_crawler.SGGTeacherCrawler',
            'CSETeacherCrawler': 'crawlers.cse_crawler.CSETeacherCrawler',
            'PMCTeacherCrawler': 'crawlers.pmc_crawler.PMCTeacherCrawler',
            'EEATeacherCrawler': 'crawlers.eea_crawler.EEATeacherCrawler',
            'JSZYTeacherCrawler': 'crawlers.jszy_crawler.JSZYTeacherCrawler',
            'MathsTeacherCrawler': 'crawlers.generic_crawler.MathsTeacherCrawler',
            'GenericTeacherCrawler': 'crawlers.generic_crawler.GenericTeacherCrawler'
        }
    
    def _load_config(self):
        """加载配置文件"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载YAML配置失败: {e}")
            return self._get_default_config()
    
    def _load_json_config(self):
        """加载JSON格式配置文件"""
        # JSON 配置加载不再支持
        logger.error("JSON 配置已被移除，请使用 YAML 配置文件 (config/colleges.yaml)")
        return self._get_default_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            'colleges': {
                'eis': {
                    'name': '电子信息学院',
                    'base_url': 'http://eis.whu.edu.cn',
                    'teacher_list_url': 'http://eis.whu.edu.cn/index/goSzdw?flag=1&newskind_id=20160320222026165YIdDsQIbgNtoE',
                    'teacher_detail_pattern': 'szdwDetail',
                    'encoding': 'utf-8',
                    'parser_class': 'EISTeacherCrawler'
                }
            },
            'global_config': {
                'delay': 1,
                'timeout': 10,
                'retry_times': 3,
                'data_dir': 'data',
                'log_level': 'INFO'
            }
        }
    
    def _auto_select_crawler_class(self, college_config):
        """
        自动选择合适的爬虫类
        
        Args:
            college_config (dict): 学院配置
            
        Returns:
            str: 爬虫类名
        """
        # 首先检查是否手动指定了爬虫类
        if 'parser_class' in college_config:
            return college_config['parser_class']
        
        # 自动检测jszy.whu.edu.cn域名
        base_url = college_config.get('base_url', '')
        teacher_list_url = college_config.get('teacher_list_url', '')
        
        # 检查URL中是否包含jszy域名
        if 'jszy.whu.edu.cn' in base_url or 'jszy.whu.edu.cn' in teacher_list_url:
            logger.info(f"检测到jszy域名，使用JSZYTeacherCrawler")
            return 'JSZYTeacherCrawler'
        
        # 默认返回通用爬虫
        return 'GenericTeacherCrawler'
    
    def _get_crawler_class(self, class_name):
        """动态获取爬虫类"""
        try:
            if class_name in self.crawler_classes:
                module_path, class_name_only = self.crawler_classes[class_name].rsplit('.', 1)
                module = importlib.import_module(module_path)
                return getattr(module, class_name_only)
            else:
                # 默认使用通用爬虫
                from crawlers.generic_crawler import GenericTeacherCrawler
                return GenericTeacherCrawler
        except ImportError as e:
            logger.error(f"导入爬虫类失败 {class_name}: {e}")
            from crawlers.generic_crawler import GenericTeacherCrawler
            return GenericTeacherCrawler

    def _auto_select_crawler_from_url(self, url):
        """
        根据URL自动选择合适的爬虫类
        
        Args:
            url (str): 要爬取的URL
            
        Returns:
            str: 爬虫类名
        """
        # jszy域名检测
        if 'jszy.whu.edu.cn' in url:
            return 'JSZYTeacherCrawler'
        
        # 其他学院域名检测  
        if 'eis.whu.edu.cn' in url:
            return 'EISTeacherCrawler'
        elif 'cs.whu.edu.cn' in url:
            return 'CSTeacherCrawler'
        elif 'rsgis.whu.edu.cn' in url:
            return 'RSGISTeacherCrawler'
        
        # 默认使用通用爬虫
        return 'GenericTeacherCrawler'

    def crawl_from_url(self, url):
        """
        从单个URL直接爬取教师信息
        
        Args:
            url (str): 要爬取的URL
            
        Returns:
            list: 教师信息列表
        """
        try:
            logger.info(f"开始从URL爬取数据: {url}")
            
            # 自动选择爬虫类型
            crawler_class_name = self._auto_select_crawler_from_url(url)
            crawler_class = self._get_crawler_class(crawler_class_name)
            
            logger.info(f"选择的爬虫类型: {crawler_class_name}")
            
            # 创建基本配置
            config = {
                'base_url': url,
                'teacher_list_url': url,
                'college_name': '自动检测学院',
                **self.config.get('global_config', {})
            }
            
            # 为不同爬虫添加特定配置
            if 'jszy.whu.edu.cn' in url:
                config.update({
                    'teacher_detail_pattern': '/jszy.whu.edu.cn/',
                    'base_url': 'https://jszy.whu.edu.cn'
                })
            elif 'eis.whu.edu.cn' in url:
                config.update({
                    'teacher_detail_pattern': 'szdwDetail',
                    'base_url': 'http://eis.whu.edu.cn'
                })
            elif 'cs.whu.edu.cn' in url:
                config.update({
                    'teacher_detail_pattern': 'info/1019/',
                    'base_url': 'https://cs.whu.edu.cn'
                })
            elif 'rsgis.whu.edu.cn' in url:
                config.update({
                    'teacher_detail_pattern': 'info/1004/',
                    'base_url': 'https://rsgis.whu.edu.cn'
                })
            
            # 创建爬虫实例
            crawler = crawler_class(config)
            
            # 如果是教师详情页面，直接解析该页面
            if hasattr(crawler, 'parse_teacher_info'):
                teachers_data = [crawler.parse_teacher_info(url)]
            else:
                # 否则尝试获取教师列表
                teachers_data = crawler.crawl_all_teachers()
            
            logger.info(f"URL爬取完成，获取 {len(teachers_data)} 条数据")
            return teachers_data
            
        except Exception as e:
            logger.error(f"从URL爬取失败 {url}: {e}")
            return []
    
    def crawl_college(self, college_code, college_config):
        """
        爬取单个学院的数据，自动处理混合URL（包括jszy域名）
        
        Args:
            college_code (str): 学院代码
            college_config (dict): 学院配置
            
        Returns:
            tuple: (学院代码, 教师数据列表)
        """
        try:
            logger.info(f"开始爬取 {college_config['name']} 数据...")
            
            # 合并全局配置和学院配置
            merged_config = {**self.config.get('global_config', {}), **college_config}
            
            # 自动检测并选择合适的爬虫类
            crawler_class_name = self._auto_select_crawler_class(college_config)
            crawler_class = self._get_crawler_class(crawler_class_name)
            
            # 创建爬虫实例获取教师链接
            crawler = crawler_class(merged_config)
            teacher_links = crawler.get_teacher_links()
            
            if not teacher_links:
                logger.warning(f"{college_config['name']} 未找到教师链接")
                return college_code, []
            
            # 处理每个教师URL，根据域名选择合适的爬虫
            teachers_data = []
            jszy_crawler = None  # 延迟初始化JSZY爬虫
            
            for i, link in enumerate(teacher_links, 1):
                logger.info(f"处理第 {i}/{len(teacher_links)} 个教师: {link}")
                
                # 检测是否为jszy域名
                if 'jszy.whu.edu.cn' in link:
                    # 使用JSZY爬虫
                    if jszy_crawler is None:
                        # 延迟初始化JSZY爬虫
                        jszy_config = {
                            'name': college_config['name'],  # 保持原学院名称
                            'base_url': 'https://jszy.whu.edu.cn',
                            'teacher_list_url': 'https://jszy.whu.edu.cn',  # 添加缺失的参数
                            'teacher_detail_pattern': 'jszy.whu.edu.cn',  # 添加缺失的参数
                            'encoding': 'utf-8',
                            'parser_class': 'JSZYTeacherCrawler',
                            **self.config.get('global_config', {})
                        }
                        jszy_crawler_class = self._get_crawler_class('JSZYTeacherCrawler')
                        jszy_crawler = jszy_crawler_class(jszy_config)
                    
                    teacher_info = jszy_crawler.parse_teacher_info(link)
                    if teacher_info:
                        teacher_info['college'] = college_config['name']  # 确保学院名称正确
                        teachers_data.append(teacher_info)
                        logger.info(f"✅ JSZY教师解析成功: {teacher_info.get('name', '未知')}")
                else:
                    # 使用原学院的爬虫
                    teacher_info = crawler.parse_teacher_info(link)
                    if teacher_info:
                        teacher_info['college'] = college_config['name']
                        teachers_data.append(teacher_info)
                        logger.info(f"✅ {college_config['name']}教师解析成功: {teacher_info.get('name', '未知')}")
                
                # 延时避免过于频繁的请求
                if i < len(teacher_links):
                    import time
                    time.sleep(merged_config.get('delay', 1))
            
            # 保存数据
            if teachers_data:
                # 使用原爬虫的保存方法
                crawler.teachers_data = teachers_data  # 临时设置数据
                crawler.save_to_json(teachers_data)
                crawler.save_to_csv(teachers_data)
            
            logger.info(f"{college_config['name']} 爬取完成，获取 {len(teachers_data)} 条数据")
            return college_code, teachers_data
            
        except Exception as e:
            logger.error(f"爬取 {college_config['name']} 失败: {e}")
            return college_code, []
    
    def crawl_all_colleges(self, college_list=None, max_workers=3):
        """
        爬取所有学院的数据
        
        Args:
            college_list (list): 要爬取的学院代码列表，None表示爬取所有
            max_workers (int): 最大并发数
            
        Returns:
            dict: {学院代码: 教师数据列表}
        """
        colleges_config = self.config.get('colleges', {})
        
        if college_list:
            # 过滤指定的学院
            colleges_to_crawl = {k: v for k, v in colleges_config.items() if k in college_list}
        else:
            colleges_to_crawl = colleges_config
        
        if not colleges_to_crawl:
            logger.warning("没有找到要爬取的学院配置")
            return {}
        
        logger.info(f"准备爬取 {len(colleges_to_crawl)} 个学院的数据")
        
        all_results = {}
        
        # 使用线程池并发爬取
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有爬取任务
            future_to_college = {
                executor.submit(self.crawl_college, code, config): code
                for code, config in colleges_to_crawl.items()
            }
            
            # 收集结果
            for future in as_completed(future_to_college):
                college_code = future_to_college[future]
                try:
                    code, data = future.result()
                    all_results[code] = data
                except Exception as e:
                    logger.error(f"学院 {college_code} 爬取出现异常: {e}")
                    all_results[college_code] = []
        
        return all_results
    
    def crawl_and_merge(self, college_list=None, save_individual=True):
        """
        爬取并合并所有学院数据
        
        Args:
            college_list (list): 要爬取的学院代码列表，None表示爬取所有
            save_individual (bool): 是否保存各学院的单独文件
            
        Returns:
            list: 合并后的所有教师数据
        """
        # 爬取所有学院数据
        all_college_data = self.crawl_all_colleges(college_list)
        
        # 收集所有数据
        all_teachers_data = []
        for college_code, teachers_data in all_college_data.items():
            if teachers_data:
                college_name = self.config['colleges'][college_code]['name']
                
                # 保存原始数据
                self.data_manager.save_raw_data(teachers_data, college_code, college_name)
                
                # 保存学院分类数据
                self.data_manager.save_college_data(teachers_data, college_name)
                
                # 添加到总数据中
                all_teachers_data.extend(teachers_data)
                
                # 可选：保存单独的学院文件（已通过save_college_data处理）
                if save_individual:
                    logger.info(f"已保存 {college_name} 分类数据")
        
        # 返回所有爬取的数据（不再进行合并）
        if all_teachers_data:
            logger.info(f"爬取完成！总共获取 {len(all_teachers_data)} 位教师信息")
            return all_teachers_data
        else:
            logger.warning("未获取到任何教师数据")
            return []
    
    def get_available_colleges(self):
        """获取可用的学院列表"""
        colleges = self.config.get('colleges', {})
        return {code: config['name'] for code, config in colleges.items()}
    
    def add_college_config(self, college_code, college_config):
        """
        添加新的学院配置
        
        Args:
            college_code (str): 学院代码
            college_config (dict): 学院配置
        """
        if 'colleges' not in self.config:
            self.config['colleges'] = {}
        
        self.config['colleges'][college_code] = college_config
        logger.info(f"已添加学院配置: {college_code} - {college_config.get('name', '')}")
    
    def test_college_crawler(self, college_code, test_url=None):
        """
        测试单个学院的爬虫
        
        Args:
            college_code (str): 学院代码
            test_url (str): 测试URL，可选
            
        Returns:
            dict: 测试结果
        """
        if college_code not in self.config.get('colleges', {}):
            return {'success': False, 'error': f'学院配置不存在: {college_code}'}
        
        try:
            college_config = self.config['colleges'][college_code]
            merged_config = {**self.config.get('global_config', {}), **college_config}
            
            # 获取爬虫类
            crawler_class_name = college_config.get('parser_class', 'GenericTeacherCrawler')
            crawler_class = self._get_crawler_class(crawler_class_name)
            
            # 创建爬虫实例
            crawler = crawler_class(merged_config)
            
            if test_url:
                # 测试解析单个页面
                teacher_info = crawler.parse_teacher_info(test_url)
                return {'success': True, 'data': teacher_info}
            else:
                # 测试获取教师链接
                links = crawler.get_teacher_links()
                return {'success': True, 'links_count': len(links), 'sample_links': links[:3]}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    """主函数，演示如何使用爬虫管理器"""
    manager = CrawlerManager()
    
    # 显示可用学院
    available_colleges = manager.get_available_colleges()
    print("可用的学院:")
    for code, name in available_colleges.items():
        print(f"  {code}: {name}")
    
    # 选择要爬取的学院
    target_colleges = ['eea']  # 可以修改为其他学院或None（爬取所有）
    
    # 开始爬取
    print(f"\n开始爬取学院: {target_colleges}")
    merged_data = manager.crawl_and_merge(college_list=target_colleges)
    
    print(f"爬取完成！共获取 {len(merged_data)} 位教师信息")


if __name__ == "__main__":
    main()