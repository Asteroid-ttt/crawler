"""
计算机学院教师爬虫
继承自基础爬虫类，实现计算机学院特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class CSTeacherCrawler(BaseTeacherCrawler):
    """计算机学院教师爬虫"""
    
    def get_teacher_links(self):
        """获取所有教师的详情页面链接和研究方向信息（包括JSZY域名链接）"""
        try:
            logger.info("开始获取计算机学院教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_data = []
            
            # 存储教师基本信息，包括研究方向
            self.teachers_basic_info = {}
            
            # 查找教师链接 - 计算机学院包含两种模式：cs域名和jszy域名
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                if not href:
                    continue
                    
                # 检查是否是教师链接
                is_teacher_link = False
                
                # CS域名教师链接模式
                if self.detail_pattern in href:
                    is_teacher_link = True
                
                # JSZY域名教师链接模式
                elif 'jszy.whu.edu.cn' in href:
                    is_teacher_link = True
                    logger.info(f"找到JSZY教师链接: {href}")
                
                if is_teacher_link:
                    # 处理相对路径和绝对路径
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(self.base_url, href)
                    
                    if full_url not in [item['url'] for item in teacher_data]:
                        teacher_name = link.get_text(strip=True)
                        # 过滤空的教师名称和非正常链接
                        if teacher_name and len(teacher_name) < 15:  # 教师名字通常不会太长
                            # 尝试从列表页提取研究方向
                            research_direction = ''
                            
                            # 查找教师链接所在的父元素，尝试提取研究方向
                            parent = link.find_parent()
                            if parent:
                                # 在同一行或相邻位置查找研究方向信息
                                parent_text = parent.get_text()
                                # 如果包含典型的研究方向关键词
                                if any(keyword in parent_text for keyword in ['数据挖掘', '机器学习', '人工智能', '网络', '系统', '算法', '软件']):
                                    # 提取括号内或冒号后的内容作为研究方向
                                    direction_match = re.search(r'[（(]([^）)]+)[）)]', parent_text)
                                    if not direction_match:
                                        direction_match = re.search(r'[：:]\s*([^\n]+)', parent_text)
                                    if direction_match:
                                        research_direction = direction_match.group(1).strip()
                            
                            teacher_info = {
                                'url': full_url,
                                'name': teacher_name,
                                'research_direction': research_direction
                            }
                            
                            # 存储基本信息供后续使用
                            self.teachers_basic_info[full_url] = teacher_info
                            
                            teacher_data.append(teacher_info)
                            logger.info(f"找到教师: {teacher_name} - {research_direction} - {full_url}")
            
            logger.info(f"共找到 {len(teacher_data)} 个教师")
            return [item['url'] for item in teacher_data]
            
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
            
            # 提取教师信息 (移除education,experience,honors,publications字段)
            teacher_info = {
                'url': url,
                'name': '',
                'contact_info': '',  # 联系方式（电话/邮箱等）
                'office_location': '',  # 办公地点
                'research_direction': '',  # 研究方向
                'supervisor_type': '',  # 导师类型
                'personal_introduction': '',  # 个人简介
                'courses_taught': '',  # 主讲课程
                'research_projects': '',  # 主要科研课题及项目
                'student_guidance': '',  # 指导学生情况
                'college': '计算机学院'
            }
            
            # 提取教师姓名 - 通常在 h3 标签中
            name_element = soup.find('h3')
            if name_element:
                teacher_info['name'] = name_element.get_text(strip=True)
            
            # 提取职称信息 - 从h5标签中提取
            title_element = soup.find('h5')
            if title_element:
                title_text = title_element.get_text(strip=True)
                logger.info(f"找到职称信息: {title_text}")
                
                # 从职称信息中提取导师类型
                if '博导' in title_text or '博士生导师' in title_text:
                    teacher_info['supervisor_type'] = '博士生导师'
                elif '硕导' in title_text or '硕士生导师' in title_text:
                    teacher_info['supervisor_type'] = '硕士生导师'
                elif '副教授' in title_text:
                    teacher_info['supervisor_type'] = '副教授'
                elif '教授' in title_text:
                    teacher_info['supervisor_type'] = '教授'
                elif '讲师' in title_text:
                    teacher_info['supervisor_type'] = '讲师'
            
            # 如果有目录页的基本信息，优先使用目录页的研究方向
            if hasattr(self, 'teachers_basic_info') and url in self.teachers_basic_info:
                basic_info = self.teachers_basic_info[url]
                if basic_info['research_direction']:
                    teacher_info['research_direction'] = basic_info['research_direction']
                    logger.info(f"使用目录页研究方向: {basic_info['research_direction']}")
            
            # 提取联系方式
            contact_section = soup.find('h5', text=re.compile(r'联系方式'))
            if contact_section:
                contact_info_list = []
                # 查找联系方式部分的内容
                contact_parent = contact_section.find_parent()
                if contact_parent:
                    contact_text = contact_parent.get_text()
                    # 提取邮箱
                    email_match = re.search(r'E-mail[：:]\s*([^\s\n]+@[^\s\n]+)', contact_text)
                    if email_match:
                        contact_info_list.append(f"邮箱: {email_match.group(1)}")
                    
                    # 提取办公电话
                    phone_match = re.search(r'办公电话[：:]\s*([^\s\n]+)', contact_text)
                    if phone_match and phone_match.group(1).strip():
                        contact_info_list.append(f"电话: {phone_match.group(1)}")
                    
                    # 提取办公地点
                    office_match = re.search(r'办公地点[：:]\s*([^\s\n]+)', contact_text)
                    if office_match and office_match.group(1).strip():
                        teacher_info['office_location'] = office_match.group(1).strip()
                
                teacher_info['contact_info'] = '; '.join(contact_info_list)
            
            # 提取详细信息段落，只更新有内容的字段
            detailed_sections = self._extract_detailed_sections(soup)
            for key, value in detailed_sections.items():
                if value:  # 只有当值非空时才更新
                    teacher_info[key] = value
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_detailed_sections(self, soup):
        """提取详细信息段落"""
        sections = {}
        
        def extract_section_content(section_title):
            """根据h3/h4标题提取对应section的内容"""
            # 查找包含指定标题的h3或h4元素
            header_elements = soup.find_all(['h3', 'h4'])
            for header in header_elements:
                header_text = header.get_text(strip=True)
                if section_title in header_text:
                    # 找到对应的内容 - 通常在下一个元素或父元素后的内容中
                    content_parts = []
                    
                    # 方法1: 查找下一个兄弟元素
                    next_sibling = header.find_next_sibling()
                    while next_sibling:
                        if next_sibling.name in ['h3', 'h4', 'h5']:  # 遇到下一个标题就停止
                            break
                        if next_sibling.name in ['p', 'div']:
                            text = next_sibling.get_text(strip=True)
                            # 确保不是标题本身，且有实际内容
                            if text and text != header_text and text != section_title and len(text) > 10:
                                content_parts.append(text)
                        next_sibling = next_sibling.find_next_sibling()
                    
                    # 方法2: 如果上面没找到内容，查找父元素的后续内容
                    if not content_parts and header.parent:
                        parent = header.parent
                        found_header = False
                        for child in parent.descendants:
                            if child == header:
                                found_header = True
                                continue
                            if found_header and child.name in ['h3', 'h4', 'h5']:
                                break
                            if found_header and hasattr(child, 'get_text'):
                                text = child.get_text(strip=True)
                                # 确保不是标题本身，且有实际内容
                                if (text and text != header_text and text != section_title 
                                    and len(text) > 10 and text not in content_parts):
                                    content_parts.append(text)
                    
                    if content_parts:
                        content = ' '.join(content_parts)
                        # 清理内容
                        content = re.sub(r'\s+', ' ', content)
                        content = content.replace('&nbsp;', ' ')
                        cleaned_content = content.strip()
                        # 再次确认不是标题本身
                        if cleaned_content and cleaned_content != section_title:
                            return cleaned_content
            return ''
        
        # 提取各个部分的信息，只有找到实际内容才设置
        research_direction = extract_section_content('研究方向')
        if research_direction:
            sections['research_direction'] = research_direction
            
        courses_taught = extract_section_content('教授课程')
        if courses_taught:
            sections['courses_taught'] = courses_taught
            
        research_projects = extract_section_content('科研课题')
        if research_projects:
            sections['research_projects'] = research_projects
            
        student_guidance = extract_section_content('研究团队')
        if student_guidance:
            sections['student_guidance'] = student_guidance
        
        # 提取个人简介，如果没有专门的简介，可以从其他部分组合
        work_experience = extract_section_content('工作经验')
        if work_experience:
            sections['personal_introduction'] = work_experience
        
        return sections