"""
动力与机械学院教师爬虫
继承自基础爬虫类，实现特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class PMCTeacherCrawler(BaseTeacherCrawler):
    """动力与机械学院教师爬虫"""

    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            teacher_links = []
            
            # 需要爬取的所有页面（包括主页面和各个系部页面）
            pages_to_crawl = [
                self.main_url,  # 主教师页面
                "https://pmc.whu.edu.cn/szdw/jsdw/dlgcx.htm",  # 动力工程系
                "https://pmc.whu.edu.cn/szdw/jsdw/jxgcx.htm",  # 机械工程系
                "https://pmc.whu.edu.cn/szdw/jsdw/nyhxgcx.htm",  # 能源化学工程系
                "https://pmc.whu.edu.cn/szdw/jsdw/syjxzx.htm"   # 实验教学中心
            ]
            
            for page_url in pages_to_crawl:
                logger.info(f"正在爬取页面: {page_url}")
                response = self.make_request(page_url)
                if not response:
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '').strip()
                    link_text = link.get_text(strip=True)
                    
                    if not href or href.startswith('javascript'):
                        continue
                    
                    # 匹配多种URL模式的教师详情页
                    is_teacher_link = False
                    if (href.endswith('.htm') and link_text and len(link_text) <= 10 and 
                        not any(keyword in link_text for keyword in 
                        ['首页', '师资队伍', '教师队伍', '正高级', '副高级', '中级', '动力工程系', 
                         '机械工程系', '能源化学工程系', '实验教学中心', '当前位置', '版权所有'])):
                        
                        # 检查是否是教师详情页的URL模式
                        if any(pattern in href for pattern in [
                            'info/' # 可能的教师
                        ]):
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
                # 兼容旧的调用方式
                url = teacher_data
                name_from_list = ""
            
            logger.info(f"正在解析教师信息: {url}")
            response = self.make_request(url)
            if not response:
                return None
            
            # 检查是否是有效页面
            if '页面未找到' in response.text or '404' in response.text:
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
            
            # 获取页面所有文本
            text = soup.get_text(separator='\n', strip=True)
            
            # 从HTML结构提取姓名
            if not teacher_info['name'] or teacher_info['name'] == '':
                # 首先尝试从partyTitle的h3标签提取姓名
                party_title = soup.find('div', class_='partyTitle')
                if party_title:
                    h3_tag = party_title.find('h3')
                    if h3_tag:
                        name_text = h3_tag.get_text(strip=True)
                        if name_text and len(name_text) >= 2 and len(name_text) <= 4:
                            teacher_info['name'] = name_text
                
                # 如果还没找到姓名，从v_news_content区域的文本中提取
                if not teacher_info['name']:
                    content_div = soup.find('div', class_='v_news_content')
                    if content_div:
                        content_text = content_div.get_text()
                        name_match = re.search(r'姓名[:：]\s*([^\n\s]{2,4})', content_text)
                        if name_match:
                            teacher_info['name'] = name_match.group(1)
            
            # 从v_news_content区域提取其他信息
            content_div = soup.find('div', class_='v_news_content')
            if content_div:
                content_text = content_div.get_text(separator='\n', strip=True)
                
                # 1. 提取职称
                title_patterns = [
                    r'职称[:：]\s*([^\n]+)',
                    r'现任[:：]\s*([^\n]+)',
                ]
                for pattern in title_patterns:
                    title_match = re.search(pattern, content_text)
                    if title_match:
                        teacher_info['supervisor_type'] = title_match.group(1).strip()
                        break
                
                # 2. 提取邮箱
                email_patterns = [
                    r'E-?mail[:：]\s*([\w.-]+@[\w.-]+)',
                    r'邮箱[:：]\s*([\w.-]+@[\w.-]+)',
                    r'([\w.-]+@whu\.edu\.cn)',
                    r'([\w.-]+@[\w.-]+\.edu\.cn)'
                ]
                for pattern in email_patterns:
                    email_match = re.search(pattern, content_text, re.IGNORECASE)
                    if email_match:
                        teacher_info['contact_info'] = f"邮箱: {email_match.group(1)}"
                        break
                
                # 3. 提取研究方向 - 寻找"研究方向"关键词所在段落
                research_patterns = [
                    r'(四、?主要研究方向.*?)(?=五、?|六、?|七、?|$)',
                    r'(主要研究方向[:：][^四五六七八九十]*?)(?=\n\n|\n[四五六七八九十]|$)',
                    r'(研究方向[:：][^四五六七八九十]*?)(?=\n\n|\n[四五六七八九十]|$)'
                ]
                for pattern in research_patterns:
                    research_match = re.search(pattern, content_text, re.DOTALL)
                    if research_match:
                        research_text = research_match.group(1).strip()
                        # 清理文本，去除编号和多余空白
                        research_text = re.sub(r'^四、?主要研究方向\s*', '', research_text)
                        research_text = re.sub(r'\s+', ' ', research_text)
                        teacher_info['research_direction'] = research_text
                        break
                
                # 4. 提取主讲课程 - 寻找"主讲课程"关键词所在段落
                course_patterns = [
                    r'(五、?主讲课程.*?)(?=六、?|七、?|八、?|$)',
                    r'(主讲课程[:：][^五六七八九十]*?)(?=\n\n|\n[五六七八九十]|$)',
                ]
                for pattern in course_patterns:
                    course_match = re.search(pattern, content_text, re.DOTALL)
                    if course_match:
                        course_text = course_match.group(1).strip()
                        # 清理文本
                        course_text = re.sub(r'^五、?主讲课程\s*', '', course_text)
                        course_text = re.sub(r'\s+', ' ', course_text)
                        teacher_info['courses_taught'] = course_text
                        break
                
                # 5. 提取个人经历和荣誉作为自我介绍
                intro_sections = []
                
                # 提取工作经历
                experience_patterns = [
                    r'(二、?学习及?工作经历.*?)(?=三、?|四、?|五、?|$)',
                    r'(工作经历[:：][^二三四五六七八九十]*?)(?=\n\n|\n[二三四五六七八九十]|$)',
                ]
                for pattern in experience_patterns:
                    exp_match = re.search(pattern, content_text, re.DOTALL)
                    if exp_match:
                        exp_text = exp_match.group(1).strip()
                        exp_text = re.sub(r'^二、?学习及?工作经历\s*', '', exp_text)
                        exp_text = re.sub(r'\s+', ' ', exp_text)
                        if exp_text:
                            intro_sections.append(f"工作经历: {exp_text}")
                        break
                
                # 提取荣誉奖励
                honor_patterns = [
                    r'(七、?主要荣誉奖励.*?)(?=八、?|九、?|十、?|$)',
                    r'(荣誉奖励[:：][^七八九十]*?)(?=\n\n|\n[七八九十]|$)',
                ]
                for pattern in honor_patterns:
                    honor_match = re.search(pattern, content_text, re.DOTALL)
                    if honor_match:
                        honor_text = honor_match.group(1).strip()
                        honor_text = re.sub(r'^七、?主要荣誉奖励\s*', '', honor_text)
                        honor_text = re.sub(r'\s+', ' ', honor_text)
                        if honor_text:
                            intro_sections.append(f"荣誉奖励: {honor_text}")
                        break
                
                # 提取学术兼职
                position_patterns = [
                    r'(三、?学术和?社会兼职.*?)(?=四、?|五、?|六、?|$)',
                    r'(学术兼职[:：][^三四五六七八九十]*?)(?=\n\n|\n[三四五六七八九十]|$)',
                ]
                for pattern in position_patterns:
                    pos_match = re.search(pattern, content_text, re.DOTALL)
                    if pos_match:
                        pos_text = pos_match.group(1).strip()
                        pos_text = re.sub(r'^三、?学术和?社会兼职\s*', '', pos_text)
                        pos_text = re.sub(r'\s+', ' ', pos_text)
                        if pos_text:
                            intro_sections.append(f"学术兼职: {pos_text}")
                        break
                
                # 合并个人介绍
                if intro_sections:
                    teacher_info['personal_introduction'] = ' | '.join(intro_sections)
                
                # 6. 提取科研项目
                project_patterns = [
                    r'(六、?学术成果.*?)(?=七、?|八、?|九、?|$)',
                    r'(科研项目[:：][^六七八九十]*?)(?=\n\n|\n[六七八九十]|$)',
                ]
                for pattern in project_patterns:
                    proj_match = re.search(pattern, content_text, re.DOTALL)
                    if proj_match:
                        proj_text = proj_match.group(1).strip()
                        proj_text = re.sub(r'^六、?学术成果\s*', '', proj_text)
                        proj_text = re.sub(r'\s+', ' ', proj_text)
                        teacher_info['research_projects'] = proj_text
                        break
                
                # 7. 提取学生指导信息 - 通常在最后
                guidance_keywords = ['热烈欢迎', '欢迎', '招收', '指导学生']
                for keyword in guidance_keywords:
                    if keyword in content_text:
                        # 提取包含关键词的最后一段
                        lines = content_text.split('\n')
                        for line in reversed(lines):
                            if keyword in line and len(line.strip()) > 10:
                                teacher_info['student_guidance'] = line.strip()
                                break
                        if teacher_info['student_guidance']:
                            break
            
            # 清理所有字段
            for key, value in teacher_info.items():
                if isinstance(value, str):
                    teacher_info[key] = value.strip()
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None