"""
新版主程序
使用重构后的架构，支持多学院爬取
"""
from crawler_manager import CrawlerManager
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 创建爬虫管理器
    # 使用 YAML 配置文件
    manager = CrawlerManager(config_path='config/colleges.yaml')
    logger.info("使用YAML配置文件")
    
    # 显示可用学院
    available_colleges = manager.get_available_colleges()
    print("=== 可用的学院 ===")
    for code, name in available_colleges.items():
        print(f"  {code}: {name}")
    
    print("\n=== 开始爬取 ===")
    
    # 方式1: 爬取所有学院
    # merged_data = manager.crawl_and_merge()
    
    # 方式2: 爬取指定学院（推荐先测试单个学院）
    target_colleges = ['rsgis']  # 运行遥感信息工程学院
    print(f"目标学院: {[available_colleges.get(code, code) for code in target_colleges]}")
    
    merged_data = manager.crawl_and_merge(college_list=target_colleges, save_individual=True)
    
    print(f"\n=== 爬取完成 ===")
    print(f"总共获取 {len(merged_data)} 位教师信息")
    print("数据已保存到 data 目录")


def test_single_college(college_code, test_url):
    """测试单个学院的爬虫
    Args:
        college_code (str): 学院代码
        test_url (str): 测试用的教师详情页URL
    """
    manager = CrawlerManager(config_path='config/colleges.yaml')
    
    # 测试电子信息学院
    result = manager.test_college_crawler(college_code, test_url=test_url)
    print("测试结果:", result)


def add_new_college_example():
    """添加新学院的示例"""
    manager = CrawlerManager(config_path='config/colleges.yaml')
    
    # 添加新的学院配置
    new_college_config = {
        'name': '物理科学与技术学院',
        'base_url': 'http://physics.whu.edu.cn',
        'teacher_list_url': 'http://physics.whu.edu.cn/teachers',
        'teacher_detail_pattern': 'teacher',
        'encoding': 'utf-8',
        'parser_class': 'GenericTeacherCrawler',  # 使用通用爬虫
        'page_structure': {
            'teacher_link_selector': 'a[href*="teacher"]',
            'extraction_patterns': {
                'name': {'selector': 'h1, .name', 'clean': True},
                'contact_info': {'selector': '.contact', 'clean': True}
            }
        }
    }
    
    manager.add_college_config('physics', new_college_config)
    print("已添加物理学院配置")


if __name__ == "__main__":
    # 运行主程序
    main()
    
    # 取消注释以下行来运行测试
    # test_single_college('eis', 'http://eis.whu.edu.cn/index/szdwDetail?rsh=00002318&newskind_id=20160320222150685844oLXklVFf7H')
    
    # 取消注释以下行来查看添加新学院的示例
    # add_new_college_example()