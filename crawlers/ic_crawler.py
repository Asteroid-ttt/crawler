"""
集成电路学院(Integrated Circuit College)教师信息爬虫
"""
import re
import logging
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ICTeacherCrawler(BaseTeacherCrawler):
    """集成电路学院教师信息爬虫"""

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
        # 根据网页结构，教师链接在 <a> 标签中，href包含 info/
        links = soup.find_all('a', href=re.compile(r'info/\d+/\d+\.htm'))
        
        for link in links:
            href = link.get('href', '')
            if href:
                # 如果是相对路径，转换为绝对路径
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
        HTML结构示例：
        <h4>姓名<span>职称</span></h4>
        <dl>
            <dt>邮箱</dt>
            <dd><span>：</span> email@example.com</dd>
        </dl>
        <dl>
            <dt>研究方向</dt>
            <dd><span>：</span> 研究方向内容</dd>
        </dl>
        <div class="v_news_content">
            <h3>教育及工作经历：</h3>
            <p>内容...</p>
            <h3>主讲课程：</h3>
            <p>内容...</p>
            <h3>主要科研项目：</h3>
            <p>内容...</p>
            <h3>代表性论文：</h3>
            <p>内容...</p>
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

        # 提取姓名和职称 - 从 <h4>姓名<span>职称</span></h4>
        h4_tag = soup.find('h4')
        if h4_tag:
            # 提取姓名（h4的直接文本）
            name_text = h4_tag.get_text(strip=True)
            span_tag = h4_tag.find('span')
            if span_tag:
                # 职称在span中
                teacher_info['supervisor_type'] = span_tag.get_text(strip=True)
                # 姓名是h4文本减去span文本
                teacher_info['name'] = name_text.replace(teacher_info['supervisor_type'], '').strip()
            else:
                teacher_info['name'] = name_text
            logger.debug(f"提取到姓名: {teacher_info['name']}, 职称: {teacher_info['supervisor_type']}")

        # 提取邮箱和研究方向 - 从 <dl> 标签
        dl_tags = soup.find_all('dl')
        for dl in dl_tags:
            dt = dl.find('dt')
            dd = dl.find('dd')
            if dt and dd:
                field_name = dt.get_text(strip=True)
                field_value = dd.get_text(strip=True)
                # 去掉可能的冒号
                field_value = re.sub(r'^[：:]\s*', '', field_value)
                
                if '邮箱' in field_name or 'email' in field_name.lower():
                    teacher_info['contact_info'] = field_value
                    logger.debug(f"提取到邮箱: {field_value}")
                elif '研究方向' in field_name:
                    teacher_info['research_direction'] = field_value
                    logger.debug(f"提取到研究方向: {field_value}")

        # 提取主要内容区域 - 从 <div class="v_news_content">
        content_div = soup.find('div', class_='v_news_content')
        if content_div:
            # 提取所有h3标题及其后面的内容
            sections = {}
            current_section = None
            current_content = []
            
            for element in content_div.children:
                if element.name == 'h3':
                    # 保存上一个section
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    # 开始新section
                    current_section = element.get_text(strip=True)
                    current_content = []
                elif element.name in ['p', 'ul', 'ol', 'div']:
                    text = element.get_text(separator='\n', strip=True)
                    if text:
                        current_content.append(text)
            
            # 保存最后一个section
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            
            # 映射sections到字段
            for section_title, section_content in sections.items():
                if '教育' in section_title or '工作经历' in section_title:
                    teacher_info['personal_introduction'] += section_title + '\n' + section_content + '\n\n'
                elif '主讲课程' in section_title or '课程' in section_title:
                    teacher_info['courses_taught'] += section_content + '\n'
                elif '科研项目' in section_title or '项目' in section_title:
                    teacher_info['research_projects'] += section_content + '\n'
                elif '论文' in section_title or '著作' in section_title or '成果' in section_title:
                    teacher_info['personal_introduction'] += section_title + '\n' + section_content + '\n\n'
                elif '学术兼职' in section_title or '社会兼职' in section_title:
                    teacher_info['personal_introduction'] += section_title + '\n' + section_content + '\n\n'
                else:
                    # 其他内容也放入个人简介
                    teacher_info['personal_introduction'] += section_title + '\n' + section_content + '\n\n'
            
            # 清理空白
            teacher_info['personal_introduction'] = teacher_info['personal_introduction'].strip()
            teacher_info['courses_taught'] = teacher_info['courses_taught'].strip()
            teacher_info['research_projects'] = teacher_info['research_projects'].strip()

        return teacher_info
