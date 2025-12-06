"""
电气与自动化学院教师爬虫
继承自基础爬虫类，实现特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class EEATeacherCrawler(BaseTeacherCrawler):
    """电气与自动化学院教师爬虫"""

    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            teacher_links = []
            
            response = self.make_request(self.main_url)
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                link_text = link.get_text(strip=True)
                
                if not href or href.startswith('javascript'):
                    continue
                
                # 匹配包含 info/ 或 jszy 的链接作为教师链接
                is_teacher_link = False
                if (href.endswith('.htm') and link_text and len(link_text) <= 15 and 
                    not any(keyword in link_text for keyword in 
                    ['首页', '师资队伍', '教师队伍', '更多', '当前位置', '版权所有', '系部'])):
                    
                    # 检查是否包含 info/ 或 jszy 的URL模式
                    if any(pattern in href for pattern in ['info/', 'jszy']):
                        is_teacher_link = True
                
                if is_teacher_link:
                    full_url = urljoin(self.base_url, href)
                    teacher_data = {'url': full_url, 'name': link_text}
                    
                    # 避免重复添加
                    if not any(existing['url'] == full_url for existing in teacher_links):
                        teacher_links.append(teacher_data)
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
                url = teacher_data
                name_from_list = ""
            
            logger.info(f"正在解析教师信息: {url}")
            response = self.make_request(url)
            if not response:
                return None
            
            if '页面未找到' in response.text or '404' in response.text:
                logger.warning(f"页面无效或不存在: {url}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_info = {
                'url': url,
                'name': name_from_list,
                'contact_info': '',
                'office_location': '',
                'research_direction': '',
                'supervisor_type': '',
                'personal_introduction': '',
                'courses_taught': '',
                'research_projects': '',
                'student_guidance': ''
            }
            
            # 从userInf区域提取基本信息
            user_inf = soup.find('div', class_='userInf')
            if user_inf:
                # 提取姓名和职称
                name_h3 = user_inf.find('h3', class_='name')
                if name_h3:
                    name_text = name_h3.get_text(strip=True)
                    # 分离姓名和职称
                    job_span = name_h3.find('span', class_='job')
                    if job_span:
                        teacher_info['supervisor_type'] = job_span.get_text(strip=True)
                        # 移除职称部分，获取纯姓名
                        name_only = name_text.replace(job_span.get_text(strip=True), '').strip()
                        if name_only and not teacher_info['name']:
                            teacher_info['name'] = name_only
                    elif not teacher_info['name']:
                        teacher_info['name'] = name_text
                
                # 提取联系信息
                inf_ul = user_inf.find('ul', class_='inf')
                if inf_ul:
                    contact_parts = []
                    for li in inf_ul.find_all('li', class_='clearfix'):
                        attr_span = li.find('span', class_='attr')
                        valve_span = li.find('span', class_='valve')
                        
                        if attr_span and valve_span:
                            attr_text = attr_span.get_text(strip=True)
                            valve_text = valve_span.get_text(strip=True)
                            
                            # 处理不同类型的联系信息
                            if '电话' in attr_text and valve_text:
                                contact_parts.append(f"电话: {valve_text}")
                            elif '邮箱' in attr_text and valve_text:
                                contact_parts.append(f"邮箱: {valve_text}")
                            elif '办公地点' in attr_text and valve_text:
                                teacher_info['office_location'] = valve_text
                    
                    if contact_parts:
                        teacher_info['contact_info'] = '; '.join(contact_parts)
            
            # 从v_news_content区域提取详细信息
            content_div = soup.find('div', class_='v_news_content')
            if content_div:
                # 获取所有的h3标题和对应内容
                h3_tags = content_div.find_all('h3')
                
                for h3 in h3_tags:
                    title = h3.get_text(strip=True)
                    
                    # 获取h3后面的内容，直到下一个h3
                    content_parts = []
                    current = h3.next_sibling
                    
                    while current and (not hasattr(current, 'name') or current.name != 'h3'):
                        if hasattr(current, 'get_text'):
                            text = current.get_text(strip=True)
                            if text:
                                content_parts.append(text)
                        elif isinstance(current, str):
                            text = current.strip()
                            if text:
                                content_parts.append(text)
                        current = current.next_sibling
                    
                    content_text = ' '.join(content_parts)
                    
                    # 根据标题分类内容
                    if '个人简介' in title:
                        teacher_info['personal_introduction'] = content_text
                    elif '研究方向' in title:
                        teacher_info['research_direction'] = content_text
                    elif '开设课程' in title or '主讲课程' in title or '课程' in title:
                        teacher_info['courses_taught'] = content_text
                    elif '科研项目' in title or '项目' in title or '课题' in title:
                        teacher_info['research_projects'] = content_text
                    elif '代表性成果' in title or '学术成果' in title or '论文' in title:
                        if teacher_info['research_projects']:
                            teacher_info['research_projects'] += f" | {content_text}"
                        else:
                            teacher_info['research_projects'] = content_text
                    elif '指导学生' in title or '学生培养' in title:
                        teacher_info['student_guidance'] = content_text
            
            # 如果没有找到结构化内容，尝试从整个内容中提取
            if not any([teacher_info['research_direction'], teacher_info['courses_taught'], 
                       teacher_info['research_projects'], teacher_info['personal_introduction']]):
                
                # 获取页面所有文本进行关键词匹配
                all_text = soup.get_text(separator='\n', strip=True)
                
                # 使用关键词匹配提取信息
                self._extract_by_keywords(all_text, teacher_info)
            
            # 清理所有字段
            for key, value in teacher_info.items():
                if isinstance(value, str):
                    teacher_info[key] = value.strip()
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_by_keywords(self, text, teacher_info):
        """使用关键词从文本中提取信息"""
        
        # 提取研究方向
        research_patterns = [
            r'研究方向[:：]\s*([^\n]+)',
            r'主要研究方向[:：]\s*([^\n]+)',
            r'研究领域[:：]\s*([^\n]+)'
        ]
        for pattern in research_patterns:
            match = re.search(pattern, text)
            if match:
                teacher_info['research_direction'] = match.group(1).strip()
                break
        
        # 提取主讲课程
        course_patterns = [
            r'开设课程[:：]\s*([^\n]+)',
            r'主讲课程[:：]\s*([^\n]+)',
            r'教授课程[:：]\s*([^\n]+)'
        ]
        for pattern in course_patterns:
            match = re.search(pattern, text)
            if match:
                teacher_info['courses_taught'] = match.group(1).strip()
                break
        
        # 提取科研项目
        project_patterns = [
            r'科研项目[:：]\s*([^\n]+)',
            r'主要项目[:：]\s*([^\n]+)',
            r'承担项目[:：]\s*([^\n]+)'
        ]
        for pattern in project_patterns:
            match = re.search(pattern, text)
            if match:
                teacher_info['research_projects'] = match.group(1).strip()
                break
        
        # 提取个人简介（通常是较长的段落）
        if not teacher_info['personal_introduction']:
            # 查找包含个人信息的段落
            lines = text.split('\n')
            intro_candidates = []
            
            for line in lines:
                line = line.strip()
                # 寻找包含学历、工作经历等信息的行
                if any(keyword in line for keyword in ['博士', '硕士', '学士', '毕业', '工作', '教授', '副教授']) and len(line) > 20:
                    intro_candidates.append(line)
            
            if intro_candidates:
                teacher_info['personal_introduction'] = ' '.join(intro_candidates[:3])  # 取前3个相关段落