"""
机器人学院教师信息爬虫
"""
import re
import logging
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RoboticsTeacherCrawler(BaseTeacherCrawler):
    """机器人学院教师信息爬虫"""

    def get_teacher_links(self, list_url=None):
        """
        获取教师详情页面链接
        """
        if list_url is None:
            list_url = self.main_url
        
        logger.info(f"正在获取列表页面: {list_url}")
        response = self.make_request(list_url)
        if not response:
            logger.warning(f"无法获取页面: {list_url}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = []
        
        # 查找所有包含教师详情链接的元素
        # 根据提供的HTML结构,教师链接通常在 <a> 标签中,href包含 info/
        links = soup.find_all('a', href=re.compile(r'info/\d+/\d+\.htm'))
        
        for link in links:
            href = link.get('href', '')
            if href:
                # 如果是相对路径,转换为绝对路径
                if href.startswith('../'):
                    href = href.replace('../', '')
                    full_url = f"{self.base_url}/{href}"
                elif href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                elif not href.startswith('http'):
                    full_url = f"{self.base_url}/{href}"
                else:
                    full_url = href
                
                if full_url not in all_links:
                    all_links.append(full_url)
                    logger.debug(f"找到教师链接: {full_url}")
        
        logger.info(f"总共找到 {len(all_links)} 个教师链接")
        return all_links

    def parse_teacher_info(self, url):
        """
        解析教师详情页面
        机器人学院只提取:姓名、联系方式、职称、个人简介(包含所有内容)
        """
        # 获取页面内容
        response = self.make_request(url)
        if not response:
            logger.warning(f"无法获取页面: {url}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
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
            'student_guidance': ''
        }

        # 提取标题中的姓名
        title_tag = soup.find('h3', class_='title')
        if title_tag:
            teacher_info['name'] = title_tag.get_text(strip=True)
            logger.debug(f"从标题提取到姓名: {teacher_info['name']}")

        # 提取主要内容区域
        content_div = soup.find('div', class_='v_news_content')
        if not content_div:
            logger.warning(f"未找到 v_news_content 区域: {url}")
            return teacher_info

        # 将整个内容作为个人简介
        teacher_info['personal_introduction'] = content_div.get_text(separator='\n', strip=True)

        # 从内容中提取关键信息
        all_text = content_div.get_text()
        
        # 提取姓名(如果标题没有提取到)
        if not teacher_info['name']:
            name_patterns = [
                r'姓名[：:]\s*([^\n\r]+)',
                r'姓\s*名[：:]\s*([^\n\r]+)'
            ]
            for pattern in name_patterns:
                match = re.search(pattern, all_text)
                if match:
                    teacher_info['name'] = match.group(1).strip()
                    logger.debug(f"从内容提取到姓名: {teacher_info['name']}")
                    break
        
        # 提取职称 - 只提取职称关键词,不包括其他内容
        title_patterns = [
            r'职称[：:]\s*([^\n\r，,。;；]+?)(?:[，,。;；\n\r]|职务|邮箱|$)',
            r'职\s*称[：:]\s*([^\n\r，,。;；]+?)(?:[，,。;；\n\r]|职务|邮箱|$)'
        ]
        for pattern in title_patterns:
            match = re.search(pattern, all_text)
            if match:
                title_text = match.group(1).strip()
                # 只保留职称部分,去掉可能跟随的其他信息
                title_text = re.split(r'职务|邮箱|研究方向|教育经历', title_text)[0].strip()
                teacher_info['supervisor_type'] = title_text
                logger.debug(f"提取到职称: {teacher_info['supervisor_type']}")
                break
        
        # 提取邮箱
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        email_match = re.search(email_pattern, all_text)
        if email_match:
            teacher_info['contact_info'] = email_match.group()
            logger.debug(f"提取到邮箱: {teacher_info['contact_info']}")
        
        # 也可以从段落中提取邮箱
        if not teacher_info['contact_info']:
            for p in content_div.find_all('p'):
                text = p.get_text(strip=True)
                if '邮箱' in text:
                    # 提取邮箱行
                    email_match = re.search(email_pattern, text)
                    if email_match:
                        teacher_info['contact_info'] = email_match.group()
                        break

        return teacher_info
