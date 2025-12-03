"""
通用学院教师爬虫模板
可以根据不同学院的页面结构进行配置化爬取
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class GenericTeacherCrawler(BaseTeacherCrawler):
    """通用学院教师爬虫"""
    
    def __init__(self, college_config):
        super().__init__(college_config)
        # 获取页面结构配置
        self.page_config = college_config.get('page_structure', {})
    
    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            
            # 使用配置的选择器查找教师链接
            link_selector = self.page_config.get('teacher_link_selector', 'a[href*="teacher"]')
            links = soup.select(link_selector)
            
            for link in links:
                href = link.get('href', '')
                if self.detail_pattern in href:
                    # 处理&amp;转义字符
                    href = href.replace('&amp;', '&')
                    full_url = urljoin(self.base_url, href)
                    if full_url not in teacher_links:
                        teacher_name = link.get_text(strip=True)
                        teacher_links.append(full_url)
                        logger.info(f"找到教师链接: {teacher_name} - {full_url}")
            
            logger.info(f"共找到 {len(teacher_links)} 个教师链接")
            return teacher_links
            
        except Exception as e:
            logger.error(f"获取教师列表失败: {e}")
            return []
    
    def parse_teacher_info(self, url):
        """解析单个教师的详情信息"""
        try:
            logger.info(f"正在解析教师信息: {url}")
            
            response = self.make_request(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 初始化教师信息
            teacher_info = {
                'url': url,
                'name': '',
                'contact_info': '',
                'office_location': '',
                'research_direction': '',
                'supervisor_type': '',
                'personal_introduction': '',
                'courses_taught': '',
                'research_projects': '',
                'student_guidance': '',
                'education': '',
                'experience': '',
                'honors': '',
                'publications': ''
            }
            
            # 使用配置的提取模式
            extraction_patterns = self.page_config.get('extraction_patterns', {})
            if extraction_patterns:
                extracted_data = self.extract_text_by_pattern(soup, extraction_patterns)
                teacher_info.update(extracted_data)
            else:
                # 使用默认的通用提取方法
                teacher_info.update(self._extract_common_info(soup))
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_common_info(self, soup):
        """通用信息提取方法"""
        info = {}
        
        # 尝试提取姓名
        name_selectors = [
            'h1', 'h2.teacher-name', '.name', '.teacher-title',
            '[class*="name"]', '[id*="name"]'
        ]
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                info['name'] = element.get_text(strip=True)
                break
        
        # 尝试提取联系信息
        contact_keywords = ['电话', '邮箱', 'email', 'phone', 'tel', 'QQ', '微信']
        contact_info = []
        
        for keyword in contact_keywords:
            elements = soup.find_all(text=lambda text: text and keyword in text)
            for element in elements:
                parent = element.parent if element.parent else None
                if parent:
                    text = parent.get_text(strip=True)
                    if text and text not in contact_info:
                        contact_info.append(text)
        
        info['contact_info'] = '; '.join(contact_info[:3])  # 取前3个联系方式
        
        # 尝试提取研究方向
        research_keywords = ['研究方向', '研究领域', '专业方向', 'research']
        for keyword in research_keywords:
            elements = soup.find_all(text=lambda text: text and keyword in text)
            for element in elements:
                parent = element.parent if element.parent else None
                if parent:
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        info['research_direction'] = next_sibling.get_text(strip=True)
                        break
            if info.get('research_direction'):
                break
        
        return info


class CSTeacherCrawler(GenericTeacherCrawler):
    """计算机学院教师爬虫"""
    pass


class MathsTeacherCrawler(GenericTeacherCrawler):
    """数学与统计学院教师爬虫"""
    pass


# 爬虫类映射
CRAWLER_CLASSES = {
    'EISTeacherCrawler': 'crawlers.eis_crawler.EISTeacherCrawler',
    'CSTeacherCrawler': 'CSTeacherCrawler',
    'MathsTeacherCrawler': 'MathsTeacherCrawler',
    'GenericTeacherCrawler': 'GenericTeacherCrawler'
}