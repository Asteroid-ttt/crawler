"""
土木建筑工程学院(Civil Engineering)教师信息爬虫
只提取姓名和完整介绍内容
"""
import re
import logging
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CIVTeacherCrawler(BaseTeacherCrawler):
    """土木建筑工程学院教师信息爬虫"""

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
        # 包含 info/ 或 jszy 的链接
        links = soup.find_all('a', href=re.compile(r'(info/\d+/\d+\.htm|jszy\.whu\.edu\.cn)'))
        
        for link in links:
            href = link.get('href', '')
            if href:
                # 处理不同类型的链接
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('../'):
                    href = href.replace('../', '')
                    full_url = f"{self.base_url}/{href}"
                elif href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"
                
                if full_url not in all_links:
                    all_links.append(full_url)
                    logger.debug(f"找到教师链接: {full_url}")
        
        logger.info(f"总共找到 {len(all_links)} 个教师链接")
        return all_links

    def parse_teacher_info(self, url):
        """
        解析教师详情页面
        根据用户要求：只需要提取姓名和介绍内容，其他内容不需要分离
        
        HTML结构示例：
        <div class="art-tit">
            <h3>姓名</h3>
        </div>
        <div class="v_news_content">
            所有内容...
        </div>
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

        # 提取姓名 - 从 <h3> 标签或标题中
        # 方法1: 从 art-tit 中的 h3 标签
        art_tit = soup.find('div', class_='art-tit')
        if art_tit:
            h3_tag = art_tit.find('h3')
            if h3_tag:
                teacher_info['name'] = h3_tag.get_text(strip=True)
                logger.debug(f"从 art-tit h3 提取到姓名: {teacher_info['name']}")
        
        # 方法2: 如果没找到，尝试其他 h3 标签
        if not teacher_info['name']:
            h3_tag = soup.find('h3')
            if h3_tag:
                teacher_info['name'] = h3_tag.get_text(strip=True)
                logger.debug(f"从 h3 提取到姓名: {teacher_info['name']}")
        
        # 方法3: 从 title 标签提取
        if not teacher_info['name']:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # 尝试提取姓名（通常在标题开头）
                name_match = re.match(r'^([^-_\|]+)', title_text)
                if name_match:
                    teacher_info['name'] = name_match.group(1).strip()
                    logger.debug(f"从 title 提取到姓名: {teacher_info['name']}")

        # 提取完整内容 - 从 v_news_content 区域
        content_div = soup.find('div', class_='v_news_content')
        if content_div:
            # 获取所有文本内容，保持段落结构
            teacher_info['personal_introduction'] = content_div.get_text(separator='\n', strip=True)
            logger.debug(f"提取到完整内容，长度: {len(teacher_info['personal_introduction'])}")
        else:
            # 如果没有 v_news_content，尝试其他可能的内容区域
            # 尝试 art-body
            art_body = soup.find('div', class_='art-body')
            if art_body:
                teacher_info['personal_introduction'] = art_body.get_text(separator='\n', strip=True)
                logger.debug(f"从 art-body 提取到内容，长度: {len(teacher_info['personal_introduction'])}")
            else:
                # 尝试 vsb_content
                vsb_content = soup.find('div', id='vsb_content')
                if vsb_content:
                    teacher_info['personal_introduction'] = vsb_content.get_text(separator='\n', strip=True)
                    logger.debug(f"从 vsb_content 提取到内容，长度: {len(teacher_info['personal_introduction'])}")
        
        # 如果没有提取到姓名，尝试从内容中提取
        if not teacher_info['name'] and teacher_info['personal_introduction']:
            # 从内容第一行或第一段提取
            lines = teacher_info['personal_introduction'].split('\n')
            if lines:
                first_line = lines[0].strip()
                # 如果第一行比较短（可能是姓名）
                if len(first_line) <= 10:
                    teacher_info['name'] = first_line
                    logger.debug(f"从内容第一行提取到姓名: {teacher_info['name']}")

        return teacher_info
