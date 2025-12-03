"""
jszy.whu.edu.cn 通用教师爬虫
处理 jszy.whu.edu.cn 域名下的教师主页
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import re

logger = logging.getLogger(__name__)

class JSZYTeacherCrawler(BaseTeacherCrawler):
    """jszy.whu.edu.cn 教师爬虫"""
    
    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取jszy域名教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            
            # 存储教师基本信息
            self.teachers_basic_info = {}
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                
                # 检查是否是jszy.whu.edu.cn的教师页面
                if self._is_jszy_teacher_link(href):
                    # 处理相对路径和绝对路径
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(self.base_url, href)
                    
                    if full_url not in teacher_links:
                        teacher_name = link.get_text(strip=True)
                        # 过滤空的教师名称和非正常链接
                        if teacher_name and len(teacher_name) < 10:
                            # 尝试从列表页提取研究方向
                            research_direction = ''
                            parent = link.find_parent()
                            if parent:
                                parent_text = parent.get_text()
                                direction_match = re.search(r'[（(]([^）)]+)[）)]', parent_text)
                                if direction_match:
                                    research_direction = direction_match.group(1).strip()
                            
                            teacher_info = {
                                'url': full_url,
                                'name': teacher_name,
                                'research_direction': research_direction
                            }
                            
                            self.teachers_basic_info[full_url] = teacher_info
                            teacher_links.append(full_url)
                            logger.info(f"找到jszy教师: {teacher_name} - {full_url}")
            
            logger.info(f"共找到 {len(teacher_links)} 个jszy教师链接")
            return teacher_links
            
        except Exception as e:
            logger.error(f"获取jszy教师列表失败: {e}")
            return []
    
    def _is_jszy_teacher_link(self, href):
        """判断是否是jszy教师页面链接"""
        if not href:
            return False
        
        # 检查是否包含jszy.whu.edu.cn
        if 'jszy.whu.edu.cn' in href:
            return True
        
        # 检查是否是相对路径但指向jszy域名
        if href.startswith('/') and 'jszy' in self.base_url:
            return True
        
        return False
    
    def parse_teacher_info(self, url):
        """解析单个教师的详情信息"""
        try:
            logger.info(f"正在解析jszy教师信息: {url}")
            
            response = self.make_request(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取教师信息
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
                'student_guidance': '',
                'college': '未知学院'  # 将在后面从页面内容中提取
            }
            
            # 提取教师姓名 - 多种方式尝试
            name_found = False
            
            # 方式1: 从页面内容中查找姓名模式
            page_text = soup.get_text()
            
            # 首先尝试URL映射（最高优先级）
            url_parts = url.rstrip('/').split('/')
            if url_parts:
                url_name = url_parts[-1]
                
                # URL名称转中文姓名的映射
                url_to_name = {
                    'zzchen': '陈震中',
                    'hetao1': '何涛', 
                    'menglingkui': '孟令奎',
                    'lixinghua2': '李星华'
                }
                
                if url_name in url_to_name:
                    teacher_info['name'] = url_to_name[url_name]
                    name_found = True
            
            # 如果URL映射没有找到，再尝试其他方式
            if not name_found:
                # 查找"教师拼音名称"或类似模式
                name_patterns = [
                    r'教师拼音名称[：:.]\s*([A-Za-z\s]+)',  # 拼音名称，然后从URL提取中文
                    r'个人简介\s*([^\n\r，。,]{2,4})[，,]',  # 个人简介后面的姓名
                    r'^([^\n\r\s]{2,4})教授',  # 开头的姓名+教授
                    r'个人信息.*?([^\n\r]{2,4})教授',
                    r'武汉大学.*?([^\n\r\s]{2,4})教授'
                ]
                
                for pattern in name_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        potential_name = match.group(1).strip()
                        # 确保是中文姓名，不是"武汉大学"等
                        if (len(potential_name) >= 2 and len(potential_name) <= 4 
                            and re.match(r'^[\u4e00-\u9fa5]{2,4}$', potential_name)
                            and potential_name not in ['武汉大学', '教授', '博士', '研究', '信息', '工程', '学院']):
                            teacher_info['name'] = potential_name
                            name_found = True
                            break
            
            # 方式2: 从标题中提取（高优先级）
            if not name_found:
                title_element = soup.find('title')
                if title_element:
                    title_text = title_element.get_text(strip=True)
                    # 从标题提取姓名：格式如 "武汉大学 何涛--中文主页--首页"
                    title_name_match = re.search(r'武汉大学\s+([^\-\s]+)', title_text)
                    if title_name_match:
                        potential_name = title_name_match.group(1).strip()
                        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', potential_name):
                            teacher_info['name'] = potential_name
                            name_found = True
                    else:
                        # 其他标题格式
                        name_match = re.search(r'([\u4e00-\u9fa5]{2,4})', title_text)
                        if name_match:
                            potential_name = name_match.group(1)
                            if potential_name not in ['武汉', '大学', '主页', '首页']:
                                teacher_info['name'] = potential_name
                                name_found = True
            
            # 方式2.5: 从页面中直接查找姓名文本
            if not name_found:
                # 查找单独出现的中文姓名
                name_search = re.search(r'(?<!\w)([^\s\n\r]{2,4})(?=\s*个人信息)', page_text)
                if name_search:
                    potential_name = name_search.group(1).strip()
                    if re.match(r'^[\u4e00-\u9fa5]{2,4}$', potential_name):
                        teacher_info['name'] = potential_name
                        name_found = True
            
            # 方式3: 从标题中提取（备用）
            if not name_found:
                title_element = soup.find('title')
                if title_element:
                    title_text = title_element.get_text(strip=True)
                    # 从标题提取姓名：格式如 "武汉大学 何涛--中文主页--首页"
                    title_name_match = re.search(r'武汉大学\s+([^\-\s]+)', title_text)
                    if title_name_match:
                        potential_name = title_name_match.group(1).strip()
                        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', potential_name):
                            teacher_info['name'] = potential_name
                            name_found = True
            
            # 如果还是没找到姓名，使用URL名称作为fallback
            if not teacher_info['name']:
                url_parts = url.rstrip('/').split('/')
                if url_parts:
                    teacher_info['name'] = url_parts[-1]
            
            # 提取联系信息
            contact_info = self._extract_contact_info(soup)
            teacher_info['contact_info'] = contact_info
            
            # 提取办公地点
            office_location = self._extract_office_location(soup)
            teacher_info['office_location'] = office_location
            
            # 如果有目录页的基本信息，使用目录页的研究方向
            if hasattr(self, 'teachers_basic_info') and url in self.teachers_basic_info:
                basic_info = self.teachers_basic_info[url]
                if basic_info['research_direction']:
                    teacher_info['research_direction'] = basic_info['research_direction']
            
            # 提取学院信息
            college_patterns = [
                r'所属院系[：:]\s*([^\n\r]+)',
                r'单位[：:]\s*([^\n\r学]+)学院',
                r'院系[：:]\s*([^\n\r]+)'
            ]
            
            for pattern in college_patterns:
                match = re.search(pattern, page_text)
                if match:
                    college = match.group(1).strip()
                    if college and len(college) < 20:
                        teacher_info['college'] = college
                        break
            
            # 提取联系信息
            contact_info_list = []
            
            # 提取邮箱
            email_patterns = [
                r'邮箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@whu\.edu\.cn)',
                r'电子邮箱[：:]\s*([^\n\r\s<]+@[^\n\r\s<]+)'
            ]
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if '@' in match and 'whu.edu.cn' in match:
                        contact_info_list.append(f"邮箱: {match.strip()}")
                        break
            
            # 提取办公地点
            office_patterns = [
                r'办公地点[：:]\s*([^\n\r。]+)',
                r'办公室[：:]\s*([^\n\r。]+)',
                r'地址[：:]\s*([^\n\r。]+)'
            ]
            
            for pattern in office_patterns:
                match = re.search(pattern, page_text)
                if match:
                    office = match.group(1).strip()
                    if office and len(office) < 50:
                        teacher_info['office_location'] = office
                        break
            
            teacher_info['contact_info'] = '; '.join(contact_info_list)
            
            # 提取详细信息
            self._extract_jszy_details(soup, teacher_info)
            
            logger.info(f"成功解析jszy教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析jszy教师信息时发生错误 {url}: {e}")
            return None
    
    def _extract_contact_info(self, soup):
        """提取联系信息"""
        contact_info_list = []
        page_text = soup.get_text()
        
        # 邮箱模式
        email_patterns = [
            r'邮\\s*箱[：:]\\s*([^\\s\\n<]+@[^\\s\\n<]+)',
            r'E-?mail[：:]\\s*([^\\s\\n<]+@[^\\s\\n<]+)',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'
        ]
        
        for pattern in email_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            for match in matches:
                if '@' in match and match not in [info['email'] for info in contact_info_list if 'email' in info]:
                    contact_info_list.append(f"邮箱: {match.strip()}")
                    break
        
        # 电话模式
        phone_patterns = [
            r'电\\s*话[：:]\\s*([\\d\\-\\+\\s()]{8,})',
            r'办公电话[：:]\\s*([\\d\\-\\+\\s()]{8,})',
            r'联系电话[：:]\\s*([\\d\\-\\+\\s()]{8,})'
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, page_text)
            if match:
                phone = match.group(1).strip()
                if len(phone) >= 8:  # 合理的电话号码长度
                    contact_info_list.append(f"电话: {phone}")
                    break
        
        return '; '.join(contact_info_list)
    
    def _extract_office_location(self, soup):
        """提取办公地点"""
        page_text = soup.get_text()
        
        office_patterns = [
            r'办公地点[：:]\\s*([^\\n\\r<]{3,})',
            r'办公室[：:]\\s*([^\\n\\r<]{3,})',
            r'地\\s*址[：:]\\s*([^\\n\\r<]{3,})',
            r'房间[：:]\\s*([^\\n\\r<]{3,})'
        ]
        
        for pattern in office_patterns:
            match = re.search(pattern, page_text)
            if match:
                office = match.group(1).strip()
                if len(office) <= 50:  # 合理的地址长度
                    return office
        
        return ''

    def _extract_jszy_details(self, soup, teacher_info):
        """提取jszy页面的详细信息"""
        page_text = soup.get_text()
        
        # 提取研究方向 - 按照标题+内容的思路
        if not teacher_info.get('research_direction'):
            research = self._extract_content_by_title(soup, ['研究方向', '研究领域', '主要研究'])
            if research:
                teacher_info['research_direction'] = research
        
        # 提取个人简介 - 从页面主要内容区域
        intro_content = []
        
        # 查找个人简介相关的内容
        intro_keywords = ['个人简介', '简介', '个人介绍', '教授', '博士', '研究']
        
        # 获取页面主要内容，排除导航
        main_content_selectors = ['.content', '.main', '.profile', '.info']
        main_content = None
        
        for selector in main_content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element
                break
        
        if not main_content:
            main_content = soup
        
        # 提取文本段落
        paragraphs = main_content.find_all(['p', 'div', 'td'])
        for p in paragraphs:
            text = p.get_text(strip=True)
            if (len(text) > 30 and 
                any(keyword in text for keyword in intro_keywords) and
                '导师' not in text[:20] and  # 排除导师信息标题
                '邮箱' not in text and
                '地址' not in text):
                
                cleaned_text = self._clean_jszy_content(text)
                if cleaned_text and len(cleaned_text) > 20:
                    intro_content.append(cleaned_text)
                    if len(intro_content) >= 3:  # 最多3个段落
                        break
        
        if intro_content:
            teacher_info['personal_introduction'] = ' '.join(intro_content)

    def _clean_jszy_content(self, text):
        """清理jszy页面的内容"""
        if not text:
            return ''
        
        # 移除常见的导航和页面结构文本
        cleaned = text
        
        # 移除导航菜单
        nav_patterns = [
            r'首页科学研究.*?语种English',
            r'首页.*?其他栏目.*?English',
            r'科学研究.*?教学研究.*?获奖信息.*?语种English',
            r'个人信息Personal information',
            r'访问量[：:].*?最后更新时间[：:].*?\.\.',
            r'开通时间[：:].*?最后更.*?',
            r'教师拼音名称.*?性别.*?职称',
            r'学历.*?性别.*?在职信息.*?所属院系'
        ]
        
        for pattern in nav_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
        
        # 移除重复的导航链接和标签
        repetitive_patterns = [
            r'(首页|科学研究|研究领域|论文成果|专利|著作成果|科研项目|科研团队|教学研究|教学资源|授课信息|教学成果|获奖信息|招生信息|学生信息|我的相册|教师博客|其他栏目|语种|English)\s*',
            r'Contact information',
            r'Personal information'
        ]
        
        for pattern in repetitive_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 移除加密邮箱字符串
        cleaned = re.sub(r'[a-f0-9]{40,}', '', cleaned)
        
        # 移除多余空白
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()

    def _extract_content_by_title(self, soup, title_keywords):
        """根据标题关键词提取对应的内容"""
        page_text = soup.get_text()
        
        # 只在页面中真正存在"研究方向"等标题时才提取
        for title_keyword in title_keywords:
            # 方法1: 在HTML结构中查找标题及其后续内容
            title_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'td', 'th', 'span'], 
                                         string=re.compile(f'^\\s*{title_keyword}\\s*$', re.IGNORECASE))
            
            for title_element in title_elements:
                # 如果是表格单元格，查找同一行的下一个单元格
                if title_element.name == 'td':
                    next_td = title_element.find_next_sibling('td')
                    if next_td:
                        content = next_td.get_text(strip=True)
                        if self._is_valid_research_content(content):
                            return self._clean_jszy_content(content)
                
                # 获取标题的下一个兄弟元素的内容
                next_sibling = title_element.find_next_sibling()
                if next_sibling:
                    content = next_sibling.get_text(strip=True)
                    if self._is_valid_research_content(content):
                        return self._clean_jszy_content(content)
        
        # 方法2: 使用正则表达式在文本中精确匹配标题模式
        for title_keyword in title_keywords:
            patterns = [
                f'{title_keyword}[：:：]\\s*([^\\n\\r。]+)',  # 标题:内容到换行或句号
                f'{title_keyword}\\s*：\\s*([^\\n\\r。]+)', # 标题：内容
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text)
                if match:
                    content = match.group(1).strip()
                    content = self._clean_jszy_content(content)
                    
                    if self._is_valid_research_content(content):
                        return content
        
        # 如果以上都没找到，返回None（不强行提取）
        return None
    
    def _is_valid_research_content(self, content):
        """判断内容是否是有效的研究方向描述"""
        if not content or len(content) < 5 or len(content) > 200:
            return False
        
        # 排除无效内容
        invalid_patterns = [
            r'profile',
            r'personal',
            r'contact',
            r'先后主持',
            r'指导研究生',
            r'获得.*奖',
            r'培养了.*名',
            r'担任.*编委'
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False
        
        # 确保包含研究相关关键词
        research_keywords = [
            '研究', '技术', '方法', '算法', '应用', '分析', '处理', '计算', 
            '智能', '学习', '遥感', '视觉', '挖掘', '测量', '系统', '检测', 
            '识别', '水利', 'GIS', '数据', '反演', '监测', '融合', '图像', '视频'
        ]
        
        return any(keyword in content for keyword in research_keywords)

    def _extract_detailed_sections(self, soup):
        """提取详细信息段落"""
        sections = {}
        page_text = soup.get_text()
        
        def extract_content_by_keywords(keywords):
            """根据关键词提取内容"""
            content_parts = []
            
            # 查找包含关键词的元素
            for element in soup.find_all(['div', 'p', 'td', 'li']):
                text = element.get_text(strip=True)
                if any(keyword in text for keyword in keywords) and len(text) > 15:
                    # 过滤掉纯标题
                    if not any(text.strip() == keyword for keyword in keywords):
                        content_parts.append(text)
            
            if content_parts:
                # 取前2个最相关的段落
                content = ' '.join(content_parts[:2])
                content = re.sub(r'\\s+', ' ', content)
                content = content.replace('&nbsp;', ' ')
                return content.strip()
            return ''
        
        # 研究方向
        if not sections.get('research_direction'):
            research_direction = extract_content_by_keywords(['研究方向', '研究领域', '研究兴趣', '主要研究'])
            if research_direction:
                sections['research_direction'] = research_direction
        
        # 个人简介
        personal_intro = extract_content_by_keywords(['个人简介', '个人概况', '基本信息', '教育经历', '工作经历'])
        if personal_intro:
            sections['personal_introduction'] = personal_intro
        
        # 主讲课程
        courses = extract_content_by_keywords(['主讲课程', '教授课程', '讲授课程', '开设课程'])
        if courses:
            sections['courses_taught'] = courses
        
        # 科研项目
        projects = extract_content_by_keywords(['科研项目', '研究项目', '主要项目', '承担项目'])
        if projects:
            sections['research_projects'] = projects
        
        # 学生指导
        guidance = extract_content_by_keywords(['指导学生', '研究团队', '学生培养', '团队成员'])
        if guidance:
            sections['student_guidance'] = guidance
        
        # 导师类型
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