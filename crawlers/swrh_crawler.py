"""
水利水电学院教师信息爬虫
"""
import re
import logging
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SWRHTeacherCrawler(BaseTeacherCrawler):
    """水利水电学院教师信息爬虫"""

    def __init__(self, college_config):
        super().__init__(college_config)
        # 水利水电学院有5个不同的列表页面
        self.list_urls = [
            "https://swrh.whu.edu.cn/szdw/zhslx.htm",    # 综合水利系
            "https://swrh.whu.edu.cn/szdw/slfdgcx1.htm", # 水力发电工程系
            "https://swrh.whu.edu.cn/szdw/swszyx.htm",   # 水务水资源系
            "https://swrh.whu.edu.cn/szdw/hlgcx1.htm",   # 河流工程系
            "https://swrh.whu.edu.cn/szdw/slgcx.htm"     # 水利工程系
        ]

    def get_teacher_links(self, list_url=None):
        """
        获取教师详情页面链接
        重写此方法以支持多个列表页面
        """
        all_links = []
        
        # 遍历所有列表页面
        for url in self.list_urls:
            logger.info(f"正在获取列表页面: {url}")
            response = self.make_request(url)
            if not response:
                logger.warning(f"无法获取页面: {url}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
        水利水电学院的教师页面有两种结构,但都包含在 div.teacher_field 中
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

        # 查找主要内容区域
        teacher_field = soup.find('div', class_='teacher_field')
        if not teacher_field:
            logger.warning(f"未找到 teacher_field 区域: {url}")
            return teacher_info

        # 提取姓名 - 从 h2 标签中获取
        name_tag = teacher_field.find('h2')
        if name_tag:
            teacher_info['name'] = name_tag.get_text(strip=True)
            logger.debug(f"提取到姓名: {teacher_info['name']}")

        # 提取主要内容区域
        content_div = teacher_field.find('div', class_='v_news_content')
        if not content_div:
            logger.warning(f"未找到 v_news_content 区域: {url}")
            return teacher_info

        # 获取所有段落和标题
        current_section = None
        section_content = {
            '个人简介': [],
            '研究方向': [],
            '开设课程': [],
            '科研项目': [],
            '代表性成果': [],
            '学生指导': [],
            '联系方式': [],
            '办公地点': []
        }

        # 遍历所有元素,根据标题分类内容
        for element in content_div.find_all(['h2', 'h3', 'p', 'div', 'span', 'strong']):
            text = element.get_text(strip=True)
            
            # 检查是否是节标题
            if element.name in ['h2', 'h3', 'strong']:
                for section_name in section_content.keys():
                    if section_name in text or self._is_section_keyword(text, section_name):
                        current_section = section_name
                        logger.debug(f"识别到章节: {section_name}")
                        break
            
            # 如果有当前节,添加内容
            elif text and current_section:
                # 过滤掉标题本身
                if not any(keyword in text for keyword in section_content.keys()):
                    section_content[current_section].append(text)

        # 将收集到的内容填充到 teacher_info
        if section_content['个人简介']:
            teacher_info['personal_introduction'] = '\n'.join(section_content['个人简介'])
        
        if section_content['研究方向']:
            teacher_info['research_direction'] = '\n'.join(section_content['研究方向'])
        
        if section_content['开设课程']:
            teacher_info['courses_taught'] = '\n'.join(section_content['开设课程'])
        
        if section_content['科研项目']:
            teacher_info['research_projects'] = '\n'.join(section_content['科研项目'])
        
        if section_content['学生指导']:
            teacher_info['student_guidance'] = '\n'.join(section_content['学生指导'])
        
        if section_content['联系方式']:
            teacher_info['contact_info'] = '\n'.join(section_content['联系方式'])
        
        if section_content['办公地点']:
            teacher_info['office_location'] = '\n'.join(section_content['办公地点'])

        # 额外处理:检查段落中是否包含联系方式和办公地点信息
        if not teacher_info['contact_info'] or not teacher_info['office_location']:
            all_paragraphs = content_div.find_all('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                
                # 查找邮箱
                if not teacher_info['contact_info'] and '@' in text:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                    if email_match:
                        teacher_info['contact_info'] = email_match.group()
                
                # 查找办公室信息
                if not teacher_info['office_location'] and ('办公室' in text or '房间' in text or '室' in text):
                    teacher_info['office_location'] = text

        # 尝试从导师类型相关文本中提取
        full_text = content_div.get_text()
        if '博士生导师' in full_text or '博导' in full_text:
            teacher_info['supervisor_type'] = '博士生导师'
        elif '硕士生导师' in full_text or '硕导' in full_text:
            teacher_info['supervisor_type'] = '硕士生导师'

        return teacher_info

    def _is_section_keyword(self, text, section_name):
        """
        检查文本是否包含某个章节的关键词
        """
        section_keywords = {
            '个人简介': ['个人简介', '简介', '基本信息', '个人情况'],
            '研究方向': ['研究方向', '研究领域', '主要研究方向'],
            '开设课程': ['开设课程', '主讲课程', '教学课程', '讲授课程'],
            '科研项目': ['科研项目', '主持项目', '参与项目', '科研成果'],
            '代表性成果': ['代表性成果', '主要成果', '科研成果', '学术成果'],
            '学生指导': ['学生指导', '研究生指导', '指导学生'],
            '联系方式': ['联系方式', '联系方法', 'Email', 'email', '邮箱', '电话'],
            '办公地点': ['办公地点', '办公室', '办公地址']
        }
        
        keywords = section_keywords.get(section_name, [])
        return any(keyword in text for keyword in keywords)
