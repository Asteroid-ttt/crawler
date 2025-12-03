"""
电子信息学院教师爬虫
继承自基础爬虫类，实现特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class EISTeacherCrawler(BaseTeacherCrawler):
    """电子信息学院教师爬虫"""
    
    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            
            # 查找教师链接，根据实际页面结构调整选择器
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                # 筛选教师详情页面的链接 - 包含szdwDetail的链接
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
            
            # 提取教师信息
            teacher_info = {
                'url': url,
                'name': '',
                'contact_info': '',  # 联系方式（电话/邮箱/QQ/微信等）
                'office_location': '',  # 办公地点
                'research_direction': '',  # 研究方向
                'supervisor_type': '',  # 导师类型
                'personal_introduction': '',  # 个人简介
                'courses_taught': '',  # 主讲课程
                'research_projects': '',  # 主要科研课题及项目
                'student_guidance': ''  # 指导学生情况
            }
            
            # 查找基本信息区域
            info_div = soup.find('div', class_='z_zp')
            
            if info_div:
                # 提取姓名
                name_element = info_div.find('p', class_='z_xie')
                if name_element:
                    teacher_info['name'] = name_element.get_text(strip=True)
                
                # 查找所有包含信息的p标签
                info_paragraphs = info_div.find_all('p')
                
                for p in info_paragraphs:
                    text = p.get_text(strip=True)
                    
                    # 提取联系方式（电话、微信、QQ）
                    if text.startswith('电话：') or '微信号：' in text or 'QQ号：' in text:
                        # 清理"电话："前缀
                        contact_text = text.replace('电话：', '').strip()
                        teacher_info['contact_info'] = contact_text
                    
                    # 提取邮箱
                    elif text.startswith('邮箱：'):
                        email = text.replace('邮箱：', '').strip()
                        if teacher_info['contact_info']:
                            teacher_info['contact_info'] += f"; 邮箱: {email}"
                        else:
                            teacher_info['contact_info'] = f"邮箱: {email}"
                    
                    # 提取办公地点
                    elif text.startswith('办公地点：'):
                        teacher_info['office_location'] = text.replace('办公地点：', '').strip()
                    
                    # 提取研究方向
                    elif text.startswith('研究方向：'):
                        teacher_info['research_direction'] = text.replace('研究方向：', '').strip()
                    
                    # 提取导师类型
                    elif text.startswith('导师类型：'):
                        teacher_info['supervisor_type'] = text.replace('导师类型：', '').strip()

            # 提取详细信息段落
            teacher_info.update(self._extract_detailed_sections(soup))
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_detailed_sections(self, soup):
        """提取详细信息段落"""
        sections = {}
        
        # 通用方法：根据h2标题提取对应的内容
        def extract_section_content(section_title):
            """根据h2标题提取对应section的内容"""
            # 查找包含指定标题的h2元素
            h2_elements = soup.find_all('h2')
            for h2 in h2_elements:
                if section_title in h2.get_text(strip=True):
                    # 找到对应的div.xe内容
                    parent_div = h2.find_parent('div')
                    if parent_div:
                        next_div = parent_div.find_next_sibling('div')
                        if next_div and 'xe' in next_div.get('class', []):
                            # 获取内容，保持换行符
                            content = next_div.get_text(separator='\n', strip=True)
                            # 清理多余的空白字符，但保留换行符
                            content = re.sub(r'[ \t]+', ' ', content)  # 只替换空格和制表符
                            content = re.sub(r'\n+', ' ', content)   # 合并多个连续换行符为单个
                            content = content.replace('&nbsp;', ' ')
                            return content.strip()
            return ''
        
        # 提取各个部分的信息
        sections['personal_introduction'] = extract_section_content('个人简介')
        sections['courses_taught'] = extract_section_content('主讲课程')
        sections['research_projects'] = extract_section_content('主要科研课题及项目')
        sections['student_guidance'] = extract_section_content('指导学生情况')
        
        return sections