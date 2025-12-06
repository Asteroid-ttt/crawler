"""
网络空间安全学院教师爬虫
继承自基础爬虫类，实现特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class CSETeacherCrawler(BaseTeacherCrawler):
    """网络空间安全学院教师爬虫"""

    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '').strip()
                link_text = link.get_text(strip=True)
                
                if not href or href.startswith('javascript'):
                    continue
                
                # 只抓取 info/ 详情页和 jszy 平台主页，并且链接文本应该是教师姓名
                if ((self.detail_pattern in href and href.endswith('.htm')) or 'jszy.whu.edu.cn' in href) and \
                   link_text and len(link_text) <= 10 and not any(keyword in link_text for keyword in 
                   ['首页', '师资队伍', '教师名录', '教授', '副教授', '讲师', '工程师', '研究员']):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in teacher_links:
                        teacher_links.append({'url': full_url, 'name': link_text})
                        logger.info(f"找到教师链接: {link_text} - {full_url}")
            logger.info(f"共找到 {len(teacher_links)} 个教师链接")
            return teacher_links
        except Exception as e:
            logger.error(f"获取教师列表失败: {e}")
            return []

    def parse_teacher_info(self, teacher_data):
        """解析单个教师的详情信息"""
        try:
            if isinstance(teacher_data, dict):
                url = teacher_data['url']
                name_from_list = teacher_data['name']
            else:
                # 兼容旧的调用方式
                url = teacher_data
                name_from_list = ""
            
            logger.info(f"正在解析教师信息: {url}")
            response = self.make_request(url)
            if not response:
                return None
            
            # 检查是否是有效页面
            if '系统提示' in response.text and '页面未找到' in response.text:
                logger.warning(f"页面无效或不存在: {url}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_info = {
                'url': url,
                'name': name_from_list,  # 优先使用列表页面的姓名
                'contact_info': '',
                'office_location': '',
                'research_direction': '',
                'supervisor_type': '',
                'personal_introduction': '',
                'courses_taught': '',
                'research_projects': '',
                'student_guidance': ''
            }
            
            # 如果姓名为空，尝试从页面提取
            if not teacher_info['name']:
                # 尝试多种方式找到教师姓名
                title_elem = soup.find('h3')
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    # 排除通用标题
                    if title_text and title_text not in ['师资队伍', '教师名录', '个人简介']:
                        teacher_info['name'] = title_text
                
                # 如果还是没有找到，尝试从页面标题提取
                if not teacher_info['name']:
                    title_tag = soup.find('title')
                    if title_tag:
                        title_text = title_tag.get_text(strip=True)
                        if '|' in title_text:
                            teacher_info['name'] = title_text.split('|')[0].strip()
                        elif '-' in title_text:
                            teacher_info['name'] = title_text.split('-')[0].strip()
            
            # 获取页面所有文本
            text = soup.get_text(separator='\n', strip=True)
            
            # 邮箱
            email_match = re.search(r'邮\s*[箱：:]\s*([\w.-]+@[\w.-]+)', text)
            if email_match:
                teacher_info['contact_info'] = f"邮箱: {email_match.group(1)}"
            
            # 电话
            phone_patterns = [
                r'电话[:：]\s*(\d{3,4}-\d{7,8})',
                r'联系电话[:：]\s*(\d{3,4}-\d{7,8})',
                r'手机[:：]\s*(1[3-9]\d{9})'
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text)
                if phone_match:
                    if teacher_info['contact_info']:
                        teacher_info['contact_info'] += f"; 电话: {phone_match.group(1)}"
                    else:
                        teacher_info['contact_info'] = f"电话: {phone_match.group(1)}"
                    break
            
            # 办公地点 - 更精确的匹配
            office_patterns = [
                r'办公室地址[:：]\s*([^\n]+)',
                r'办公地点[:：]\s*([^\n]+)',
                r'办公室[:：]\s*([^\n]+)',
                r'地址[:：]\s*([^\n]+楼[^\n]*)'
            ]
            for pattern in office_patterns:
                office_match = re.search(pattern, text)
                if office_match:
                    office_text = office_match.group(1).strip()
                    # 过滤掉无意义的内容
                    if office_text and not any(keyword in office_text for keyword in 
                               ['师资队伍', '高层次人才', '教师名录', '导航', '首页', '校本部', '新校区']):
                        teacher_info['office_location'] = office_text
                        break
            
            # 职称/导师类型
            if '博士生导师' in text:
                teacher_info['supervisor_type'] = '博士生导师'
            elif '硕士生导师' in text:
                teacher_info['supervisor_type'] = '硕士生导师'
            elif '教授' in text:
                teacher_info['supervisor_type'] = '教授'
            elif '副教授' in text:
                teacher_info['supervisor_type'] = '副教授'
            elif '讲师' in text:
                teacher_info['supervisor_type'] = '讲师'
            
            # 使用CSS选择器提取结构化信息
            def extract_teacher_section(section_name):
                """从teacher-cont结构中提取特定章节内容"""
                try:
                    # 查找包含指定章节名的h3标题的div
                    teacher_divs = soup.find_all('div', class_='teacher-cont')
                    for div in teacher_divs:
                        h3 = div.find('h3')
                        if h3 and section_name in h3.get_text(strip=True):
                            # 提取该div中除了h3之外的所有文本
                            content_parts = []
                            for element in div.find_all(['p', 'div'], recursive=True):
                                if element.name != 'h3' and element.get_text(strip=True):
                                    content_parts.append(element.get_text(strip=True))
                            
                            if content_parts:
                                content = ' '.join(content_parts)
                                # 清理内容
                                content = re.sub(r'\s+', ' ', content).strip()
                                return content[:1000] if len(content) > 1000 else content
                except Exception as e:
                    logger.warning(f"提取 {section_name} 章节时出错: {e}")
                return ''
            
            # 传统的文本搜索方式作为备用
            def extract_section_fallback(keywords, max_length=1000):
                for keyword in keywords:
                    # 匹配关键词后的内容，直到遇到下一个标题或换行
                    pattern = rf'{keyword}[:：]?\s*([^\n]+(?:\n[^A-Za-z\u4e00-\u9fa5]*[^\n]*)*?)(?=\n[A-Za-z\u4e00-\u9fa5]+[:：]|$)'
                    match = re.search(pattern, text, re.MULTILINE)
                    if match:
                        content = match.group(1).strip()
                        # 清理内容
                        content = re.sub(r'\n+', ' ', content)
                        content = content[:max_length] if len(content) > max_length else content
                        if len(content) > 10:  # 过滤太短的内容
                            return content
                return ''
            
            # 提取各个章节信息，优先使用结构化方法，备用传统文本搜索
            
            # 研究方向
            research_direction = extract_teacher_section('研究方向')
            if not research_direction:
                research_direction = extract_section_fallback(['研究方向', '主要研究方向'])
            teacher_info['research_direction'] = research_direction
            
            # 个人简介
            personal_intro = extract_teacher_section('个人简介')
            if not personal_intro:
                personal_intro = extract_section_fallback(['个人简介', '简介'], 2000)
            teacher_info['personal_introduction'] = personal_intro
            
            # 如果结构化方法没有找到研究方向，从个人简介中提取
            if not teacher_info['research_direction'] and personal_intro:
                research_patterns = [
                    r'主要研究方向[是为]?[:：]?([^。]+)',
                    r'研究方向[是为]?[:：]?([^。]+)',
                    r'研究领域[是为]?[:：]?([^。]+)',
                    r'从事([^，。]*(?:安全|计算|网络|密码|算法|系统)[^，。]*)',
                    r'专业方向[是为]?[:：]?([^。]+)'
                ]
                
                for pattern in research_patterns:
                    match = re.search(pattern, personal_intro)
                    if match:
                        research_text = match.group(1).strip()
                        research_text = re.sub(r'\s+', ' ', research_text)
                        research_text = research_text.replace('、', '，')
                        if len(research_text) > 10 and len(research_text) < 300:
                            teacher_info['research_direction'] = research_text
                            break
            
            # 教授课程
            courses = extract_teacher_section('教授课程')
            if not courses:
                courses = extract_section_fallback(['教授课程', '主讲课程', '开设课程'])
            teacher_info['courses_taught'] = courses
            
            # 科研项目
            projects = extract_teacher_section('课题科研')
            if not projects:
                projects = extract_section_fallback(['科研项目', '主要项目', '课题科研', '研究项目'])
            teacher_info['research_projects'] = projects
            
            # 教育背景
            education = extract_teacher_section('教育背景')
            if not education:
                education = extract_section_fallback(['教育背景', '学历'])
            
            # 工作经验
            experience = extract_teacher_section('工作经验')
            if not experience:
                experience = extract_section_fallback(['工作经验', '工作经历'])
            
            # 将教育背景和工作经验合并到个人简介中，如果个人简介为空的话
            if not teacher_info['personal_introduction']:
                intro_parts = []
                if education:
                    intro_parts.append(f"教育背景: {education}")
                if experience:
                    intro_parts.append(f"工作经验: {experience}")
                if intro_parts:
                    teacher_info['personal_introduction'] = ' '.join(intro_parts)
            
            # 学生指导
            teacher_info['student_guidance'] = extract_section_fallback(['指导学生', '指导研究生', '学生培养'])
            
            # 清理所有字段
            for key, value in teacher_info.items():
                if isinstance(value, str):
                    teacher_info[key] = value.strip()
                    # 移除过长的重复内容
                    if len(teacher_info[key]) > 500 and key in ['office_location', 'contact_info']:
                        teacher_info[key] = teacher_info[key][:200] + '...'
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
