"""
城市设计学院教师信息爬虫
"""
import re
import logging
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SUDTeacherCrawler(BaseTeacherCrawler):
    """城市设计学院教师信息爬虫"""

    def __init__(self, college_config):
        super().__init__(college_config)
        # 城市设计学院有8个不同的列表页面
        self.list_urls = [
            "https://sud.whu.edu.cn/szdw/jxtd/csghx/js.htm",       # 城市规划系-教授
            "https://sud.whu.edu.cn/szdw/jxtd/csghx/fjs.htm",      # 城市规划系-副教授
            "https://sud.whu.edu.cn/szdw/jxtd/jzx/js.htm",         # 建筑系-教授
            "https://sud.whu.edu.cn/szdw/jxtd/jzx/fjs.htm",        # 建筑系-副教授
            "https://sud.whu.edu.cn/szdw/jxtd/sjx/js.htm",         # 设计系-教授
            "https://sud.whu.edu.cn/szdw/jxtd/sjx/fjs.htm",        # 设计系-副教授
            "https://sud.whu.edu.cn/szdw/jxtd/txyszjsx/js.htm",    # 图学与数字技术系-教授
            "https://sud.whu.edu.cn/szdw/jxtd/txyszjsx/fjs.htm"    # 图学与数字技术系-副教授
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
                        # 处理多层相对路径
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
        城市设计学院的教师页面有两种结构,都包含在 div.item 和 div.cont 中
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

        # 提取基本信息 - 从 div.item 中获取
        item_div = soup.find('div', class_='item')
        if item_div:
            # 提取姓名
            name_tag = item_div.find('h3', class_='name')
            if name_tag:
                teacher_info['name'] = name_tag.get_text(strip=True)
                logger.debug(f"提取到姓名: {teacher_info['name']}")
            
            # 提取职称(可能是导师类型)
            zc_tag = item_div.find('h4', class_='zc')
            if zc_tag:
                zc_text = zc_tag.get_text(strip=True)
                if '教授' in zc_text or '副教授' in zc_text or '讲师' in zc_text:
                    # 职称信息可以存储到导师类型或其他字段
                    pass
            
            # 提取联系信息
            text_tags = item_div.find_all('p', class_='text')
            for p in text_tags:
                text = p.get_text(strip=True)
                if '邮箱' in text or '@' in text:
                    teacher_info['contact_info'] = text.replace('邮箱：', '').replace('邮箱:', '').strip()
                elif '部门' in text:
                    # 部门信息可以存储到办公地点
                    teacher_info['office_location'] = text.replace('部门：', '').replace('部门:', '').strip()
                elif '地址' in text or '办公室' in text:
                    teacher_info['office_location'] = text

        # 提取主要内容区域
        content_div = soup.find('div', class_='v_news_content')
        if not content_div:
            logger.warning(f"未找到 v_news_content 区域: {url}")
            return teacher_info

        # 获取所有段落和标题
        current_section = None
        section_content = {
            '教育经历': [],
            '个人简介': [],
            '研究方向': [],
            '教育与研究方向': [],
            '开设课程': [],
            '科研项目': [],
            '研究项目': [],
            '代表性成果': [],
            '学生指导': [],
            '指导博士硕士研究生': [],
            '教学与指导工作': [],
            '工作经历': [],
            '专业资质': [],
            '荣誉': [],
            '出版情况': [],
            '设计实践': []
        }

        # 遍历所有元素,根据标题分类内容
        for element in content_div.find_all(['h2', 'h3', 'p', 'div', 'span', 'strong', 'table']):
            # 跳过表格(通常是结构化的基本信息)
            if element.name == 'table':
                continue
                
            text = element.get_text(strip=True)
            
            # 检查是否是节标题
            if element.name in ['h2', 'h3', 'strong']:
                section_found = False
                for section_name in section_content.keys():
                    if section_name in text or self._is_section_keyword(text, section_name):
                        current_section = section_name
                        logger.debug(f"识别到章节: {section_name}")
                        section_found = True
                        break
                
                # 如果没有匹配到标准章节,但是是标题,重置current_section
                if not section_found and element.name in ['h2', 'h3']:
                    # 对于非标准章节标题,尝试映射到已有字段
                    if any(kw in text for kw in ['教育', '学习', '学位']):
                        current_section = '教育经历'
                    elif any(kw in text for kw in ['研究', '方向', '领域']):
                        current_section = '研究方向'
                    elif any(kw in text for kw in ['项目', '课题']):
                        current_section = '科研项目'
            
            # 如果有当前节,添加内容
            elif text and current_section:
                # 过滤掉标题本身和空内容
                if len(text) > 2 and not any(keyword in text for keyword in section_content.keys()):
                    section_content[current_section].append(text)

        # 将收集到的内容填充到 teacher_info
        # 个人简介
        if section_content['个人简介']:
            teacher_info['personal_introduction'] = '\n'.join(section_content['个人简介'])
        if section_content['教育经历']:
            intro = teacher_info['personal_introduction']
            edu = '\n教育经历:\n' + '\n'.join(section_content['教育经历'])
            teacher_info['personal_introduction'] = (intro + '\n' + edu).strip()
        if section_content['工作经历']:
            intro = teacher_info['personal_introduction']
            work = '\n工作经历:\n' + '\n'.join(section_content['工作经历'])
            teacher_info['personal_introduction'] = (intro + '\n' + work).strip()
        
        # 研究方向
        if section_content['研究方向']:
            teacher_info['research_direction'] = '\n'.join(section_content['研究方向'])
        if section_content['教育与研究方向']:
            rd = teacher_info['research_direction']
            edu_rd = '\n' + '\n'.join(section_content['教育与研究方向'])
            teacher_info['research_direction'] = (rd + '\n' + edu_rd).strip()
        if section_content['专业资质']:
            rd = teacher_info['research_direction']
            zz = '\n专业资质:\n' + '\n'.join(section_content['专业资质'])
            teacher_info['research_direction'] = (rd + '\n' + zz).strip()
        
        # 开设课程
        if section_content['开设课程']:
            teacher_info['courses_taught'] = '\n'.join(section_content['开设课程'])
        if section_content['教学与指导工作']:
            ct = teacher_info['courses_taught']
            teaching = '\n教学与指导工作:\n' + '\n'.join(section_content['教学与指导工作'])
            teacher_info['courses_taught'] = (ct + '\n' + teaching).strip()
        
        # 科研项目
        if section_content['科研项目']:
            teacher_info['research_projects'] = '\n'.join(section_content['科研项目'])
        if section_content['研究项目']:
            rp = teacher_info['research_projects']
            research = '\n' + '\n'.join(section_content['研究项目'])
            teacher_info['research_projects'] = (rp + '\n' + research).strip()
        if section_content['荣誉']:
            rp = teacher_info['research_projects']
            honor = '\n荣誉奖励:\n' + '\n'.join(section_content['荣誉'])
            teacher_info['research_projects'] = (rp + '\n' + honor).strip()
        if section_content['出版情况']:
            rp = teacher_info['research_projects']
            pub = '\n出版情况:\n' + '\n'.join(section_content['出版情况'])
            teacher_info['research_projects'] = (rp + '\n' + pub).strip()
        if section_content['设计实践']:
            rp = teacher_info['research_projects']
            design = '\n设计实践:\n' + '\n'.join(section_content['设计实践'])
            teacher_info['research_projects'] = (rp + '\n' + design).strip()
        if section_content['代表性成果']:
            rp = teacher_info['research_projects']
            achievement = '\n代表性成果:\n' + '\n'.join(section_content['代表性成果'])
            teacher_info['research_projects'] = (rp + '\n' + achievement).strip()
        
        # 学生指导
        if section_content['学生指导']:
            teacher_info['student_guidance'] = '\n'.join(section_content['学生指导'])
        if section_content['指导博士硕士研究生']:
            sg = teacher_info['student_guidance']
            guidance = '\n' + '\n'.join(section_content['指导博士硕士研究生'])
            teacher_info['student_guidance'] = (sg + '\n' + guidance).strip()

        # 额外处理:检查段落中是否包含联系方式和办公地点信息
        if not teacher_info['contact_info']:
            all_paragraphs = content_div.find_all('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                # 查找邮箱
                if '@' in text:
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                    if email_match:
                        teacher_info['contact_info'] = email_match.group()
                        break

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
            '教育经历': ['教育经历', '教育背景', '学习经历'],
            '个人简介': ['个人简介', '简介', '基本信息', '个人情况'],
            '研究方向': ['研究方向', '研究领域', '主要研究方向'],
            '教育与研究方向': ['教育与研究方向', '研究与教学'],
            '开设课程': ['开设课程', '主讲课程', '教学课程', '讲授课程'],
            '科研项目': ['科研项目', '主持项目', '参与项目'],
            '研究项目': ['研究项目', '主要项目'],
            '代表性成果': ['代表性成果', '主要成果', '科研成果', '学术成果'],
            '学生指导': ['学生指导', '研究生指导', '指导学生'],
            '指导博士硕士研究生': ['指导博士硕士', '指导研究生'],
            '教学与指导工作': ['教学与指导', '教学工作'],
            '工作经历': ['工作经历', '工作履历', '任职经历'],
            '专业资质': ['专业资质', '社会兼职', '学术兼职'],
            '荣誉': ['荣誉', '奖励', '获奖'],
            '出版情况': ['出版情况', '著作', '出版物'],
            '设计实践': ['设计实践', '实践项目', '工程实践']
        }
        
        keywords = section_keywords.get(section_name, [])
        return any(keyword in text for keyword in keywords)
