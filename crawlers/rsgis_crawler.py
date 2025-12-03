"""
遥感学院教师爬虫
继承自基础爬虫类，实现遥感学院特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class RSGISTeacherCrawler(BaseTeacherCrawler):
    """遥感学院教师爬虫"""
    
    def get_teacher_links(self):
        """获取所有教师的详情页面链接（包括RSGIS域名和JSZY域名）"""
        try:
            logger.info("开始获取遥感学院教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_data = []
            
            # 存储教师基本信息，包括研究方向
            self.teachers_basic_info = {}
            
            # 查找教师链接 - 包括遥感学院域名和jszy域名
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                is_teacher_link = False
                
                # 检查是否是遥感学院的教师详情页面
                if self.detail_pattern in href:
                    is_teacher_link = True
                # 检查是否是jszy域名的教师页面
                elif 'jszy.whu.edu.cn' in href:
                    is_teacher_link = True
                
                if is_teacher_link:
                    # 处理相对路径和绝对路径
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(self.base_url, href)
                    
                    if full_url not in [item['url'] for item in teacher_data]:
                        teacher_name = link.get_text(strip=True)
                        # 过滤空的教师名称和非正常链接
                        if teacher_name and len(teacher_name) < 10:  # 教师名字通常不会太长
                            # 尝试从列表页提取研究方向
                            research_direction = ''
                            
                            # 查找教师链接所在的父元素，尝试提取研究方向
                            parent = link.find_parent()
                            if parent:
                                # 在同一行或相邻位置查找研究方向信息
                                parent_text = parent.get_text()
                                # 如果包含典型的研究方向关键词
                                if any(keyword in parent_text for keyword in ['遥感', '地理', '测绘', '信息', '系统', '地球', '空间']):
                                    # 提取括号内或冒号后的内容作为研究方向
                                    direction_match = re.search(r'[（(]([^）)]+)[）)]', parent_text)
                                    if not direction_match:
                                        direction_match = re.search(r'[：:]\\s*([^\\n]+)', parent_text)
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
            
            # 提取教师信息
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
                'college': '遥感信息工程学院'
            }
            
            # 提取教师姓名 - 通常在标题中
            title_element = soup.find('title')
            if title_element:
                title_text = title_element.get_text(strip=True)
                # 从标题中提取姓名，通常格式为 "姓名 - 网站名"
                if '-' in title_text:
                    teacher_info['name'] = title_text.split('-')[0].strip()
                else:
                    teacher_info['name'] = title_text.strip()
            
            # 如果没有从title提取到，尝试从h1或其他元素
            if not teacher_info['name']:
                name_element = soup.find('h1') or soup.find('h2') or soup.find('h3')
                if name_element:
                    teacher_info['name'] = name_element.get_text(strip=True)
            
            # 提取联系信息和办公地点 - 从页面特定区域提取
            page_text = soup.get_text()
            contact_info_list = []
            
            # 提取办公地点 - 遥感学院页面格式特殊
            office_match = re.search(r'办公地点[：:]\s*([^\n\r。]+)', page_text)
            if office_match:
                office_location = office_match.group(1).strip()
                # 清理办公地点信息
                office_location = re.sub(r'研究方向.*$', '', office_location)
                office_location = re.sub(r'个人主页.*$', '', office_location)
                teacher_info['office_location'] = office_location.strip()
            
            # 单独提取研究方向
            research_match = re.search(r'研究方向[：:]\s*([^\n\r]+?)(?:个人主页|$)', page_text)
            if research_match:
                research_direction = research_match.group(1).strip()
                # 清理研究方向信息，移除办公地点等
                research_direction = re.sub(r'办公地点[：:].*?(?=研究方向|$)', '', research_direction)
                research_direction = re.sub(r'单位[：:].*?(?=研究方向|$)', '', research_direction)
                if research_direction and not teacher_info.get('research_direction'):
                    teacher_info['research_direction'] = research_direction
            
            # 提取邮箱
            email_patterns = [
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})',
                r'邮\\s*箱[：:]\\s*([^\\s\\n<]+@[^\\s\\n<]+)'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if '@' in match and 'whu.edu.cn' in match:  # 优先武大邮箱
                        contact_info_list.append(f"邮箱: {match.strip()}")
                        break
            
            # 提取电话
            phone_patterns = [
                r'电\\s*话[：:]\\s*([\\d\\-\\+\\s()]{8,15})',
                r'办公电话[：:]\\s*([\\d\\-\\+\\s()]{8,15})'
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, page_text)
                if match:
                    phone = match.group(1).strip()
                    if len(phone) >= 8:
                        contact_info_list.append(f"电话: {phone}")
                        break
            
            teacher_info['contact_info'] = '; '.join(contact_info_list)
            
            # 如果有目录页的基本信息，优先使用目录页的研究方向
            if hasattr(self, 'teachers_basic_info') and url in self.teachers_basic_info:
                basic_info = self.teachers_basic_info[url]
                if basic_info['research_direction']:
                    teacher_info['research_direction'] = basic_info['research_direction']
                    logger.info(f"使用目录页研究方向: {basic_info['research_direction']}")
            
            # 提取详细信息段落，只更新有内容且当前字段为空的字段
            detailed_sections = self._extract_detailed_sections(soup, teacher_info)
            for key, value in detailed_sections.items():
                if value and not teacher_info.get(key):  # 只有当值非空且当前字段为空时才更新
                    teacher_info[key] = value
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_detailed_sections(self, soup, teacher_info=None):
        """提取详细信息段落"""
        if teacher_info is None:
            teacher_info = {}
        
        sections = {}
        
        # 获取主要内容区域，排除导航
        main_content = soup.find('div', class_='main-content') or soup.find('div', class_='content') or soup
        
        def extract_section_by_keywords(keywords, section_name):
            """根据关键词提取段落内容"""
            content_parts = []
            seen_content = set()  # 避免重复内容
            
            # 查找包含关键词的段落
            paragraphs = main_content.find_all(['p', 'div', 'td', 'span'])
            for p in paragraphs:
                text = p.get_text(strip=True)
                if any(keyword in text for keyword in keywords) and len(text) > 20:
                    # 清理文本
                    cleaned_text = self._clean_extracted_text(text)
                    
                    # 确保不是标题本身，且内容不重复，且清理后有内容
                    if (cleaned_text 
                        and not any(text.strip() == keyword for keyword in keywords) 
                        and cleaned_text not in seen_content 
                        and len(cleaned_text) > 10  # 清理后还有足够内容
                        and len(cleaned_text) < 200):  # 限制单个段落长度
                        content_parts.append(cleaned_text)
                        seen_content.add(cleaned_text)
                        if len(content_parts) >= 2:  # 最多取2个段落
                            break
            
            return ' '.join(content_parts).strip() if content_parts else ''

        # 提取各个部分的信息，只有找到实际内容且当前字段为空才设置
        if not sections.get('research_direction') and not teacher_info.get('research_direction'):  # 如果都没有内容
            research_direction = extract_section_by_keywords(['研究方向', '研究领域', '主要研究'], 'research_direction')
            if research_direction:
                sections['research_direction'] = research_direction
                
        courses_taught = extract_section_by_keywords(['主讲课程', '教授课程', '讲授'], 'courses_taught')
        if courses_taught:
            sections['courses_taught'] = courses_taught
            
        research_projects = extract_section_by_keywords(['科研项目', '主要项目', '研究项目'], 'research_projects')
        if research_projects:
            sections['research_projects'] = research_projects

        return sections

    def _clean_extracted_text(self, text):
        """清理提取的文本内容"""
        if not text:
            return ''
        
        # 移除常见的导航和重复信息
        cleaned = text
        
        # 移除导航路径
        cleaned = re.sub(r'师资队伍.*?正文', '', cleaned)
        cleaned = re.sub(r'当前位置.*?>', '', cleaned)
        cleaned = re.sub(r'当前位置[：:].*?>', '', cleaned)
        
        # 移除页面结构元素
        cleaned = re.sub(r'上一篇：.*?下一篇：.*?$', '', cleaned)
        cleaned = re.sub(r'作者：.*?时间：.*?浏览：', '', cleaned)
        cleaned = re.sub(r'单　　位：', '单位：', cleaned)
        
        # 移除重复的标题信息
        lines = cleaned.split('\n')
        unique_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            if line and line not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line)
        
        cleaned = ' '.join(unique_lines)
        
        # 标准化空格
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.replace('&nbsp;', ' ')
        
        return cleaned.strip()
            
        student_guidance = extract_section_by_keywords(['指导学生', '研究团队', '学生培养'], 'student_guidance')
        if student_guidance:
            sections['student_guidance'] = student_guidance
        
        # 提取个人简介/工作经历
        personal_intro = extract_section_by_keywords(['个人简介', '工作经历', '学习经历', '教育背景'], 'personal_introduction')
        if personal_intro:
            sections['personal_introduction'] = personal_intro
        
        # 提取导师类型
        if '博导' in page_text or '博士生导师' in page_text:
            sections['supervisor_type'] = '博士生导师'
        elif '硕导' in page_text or '硕士生导师' in page_text:
            sections['supervisor_type'] = '硕士生导师'
        elif '教授' in page_text:
            sections['supervisor_type'] = '教授'
        elif '副教授' in page_text:
            sections['supervisor_type'] = '副教授'
        elif '讲师' in page_text:
            sections['supervisor_type'] = '讲师'
        
        return sections