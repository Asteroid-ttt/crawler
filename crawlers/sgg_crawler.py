"""
测绘学院教师爬虫
继承自基础爬虫类，实现特定的解析逻辑
"""
from .base_crawler import BaseTeacherCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import re

logger = logging.getLogger(__name__)

class SGGTeacherCrawler(BaseTeacherCrawler):
    """测绘学院教师爬虫"""
    
    def _is_teacher_link(self, href):
        """判断是否为有效的教师详情链接"""
        if not href or href.startswith('javascript') or href.startswith('mailto:'):
            return False

        normalized_href = href.replace('&amp;', '&')

        # 配置中定义的主要匹配模式
        pattern = self.detail_pattern
        if pattern and pattern in normalized_href:
            return True

        # 兼容测绘学院使用的教师个人主页平台 (jszy.whu.edu.cn)
        if 'jszy.whu.edu.cn' in normalized_href:
            return True

        # 测绘学院部分教师详情位于 szdw/ 路径下，链接通常以 .htm 结尾
        if 'szdw/' in normalized_href and normalized_href.endswith('.htm'):
            return True

        # fallback: 匹配常见的 info/1234/5678.htm 结构
        if re.search(r'info/\d+/\d+\.htm$', normalized_href):
            return True

        return False

    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            response = self.make_request(self.main_url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '').strip()
                if not href:
                    continue
                
                # 去掉锚点
                href = href.split('#')[0]

                if not self._is_teacher_link(href):
                    continue

                full_url = urljoin(self.base_url, href)
                if full_url in teacher_links:
                    continue

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
            
            # 初始化教师信息
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
            
            # 1. 提取姓名
            # 优先使用页面Title，通常格式为 "姓名-武汉大学测绘学院"
            page_title = soup.title.string if soup.title else ""
            if page_title:
                # 提取 - 之前的部分
                name_match = re.search(r'^([^-]+)', page_title)
                if name_match:
                    teacher_info['name'] = name_match.group(1).strip()
            
            # 如果Title提取失败，尝试查找 h1, h2 等
            if not teacher_info['name']:
                header = soup.find(['h1', 'h2', 'div'], class_=re.compile(r'tit|title', re.I))
                if header:
                    teacher_info['name'] = header.get_text(strip=True)

            # 2. 全文正则匹配基本信息
            # 使用 body 的文本进行匹配，以防信息不在 content_div 中
            body_text = soup.body.get_text(separator='\n', strip=True) if soup.body else ""
            
            contact_list = []
            # 电话
            phone_match = re.search(r'(办公电话|电话)[:：]\s*([0-9-]+)', body_text)
            if phone_match:
                contact_list.append(f"电话: {phone_match.group(2)}")
            
            # 邮箱
            email_match = re.search(r'(电子邮件|邮箱|Email)[:：]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', body_text, re.IGNORECASE)
            if email_match:
                contact_list.append(f"邮箱: {email_match.group(2)}")
            
            # QQ
            qq_match = re.search(r'QQ[:：]\s*(\d+)', body_text, re.IGNORECASE)
            if qq_match:
                contact_list.append(f"QQ: {qq_match.group(1)}")
                
            teacher_info['contact_info'] = '; '.join(contact_list)

            # 通讯地址/办公地点
            addr_match = re.search(r'(通讯地址|办公地点)[:：]\s*(.+)', body_text)
            if addr_match:
                teacher_info['office_location'] = addr_match.group(2).strip()

            # 研究方向
            research_match = re.search(r'研究方向[:：]\s*(.+)', body_text)
            if research_match:
                teacher_info['research_direction'] = research_match.group(1).strip()
            
            # 主讲课程 (正则补充)
            course_match = re.search(r'主讲课程[:：]\s*(.+)', body_text)
            if course_match:
                teacher_info['courses_taught'] = course_match.group(1).strip()

            # 导师类型
            if "博士生导师" in body_text:
                teacher_info['supervisor_type'] = "博士生导师"
            elif "硕士生导师" in body_text:
                teacher_info['supervisor_type'] = "硕士生导师"

            # 3. 提取大段落信息
            # 仍然尝试定位主要内容区域，避免抓取到页脚等无关信息
            content_div = soup.find('div', id=re.compile(r'vsb_content.*')) or \
                          soup.find('div', class_='v_news_content') or \
                          soup.body
            
            if content_div:
                lines = content_div.get_text(separator='\n').split('\n')
                
                sections_map = {
                    'personal_introduction': ['个人简介', '教育背景', '工作经历'],
                    'courses_taught': ['主讲课程', '教学情况'],
                    'research_projects': ['科研项目', '科研课题'],
                    'student_guidance': ['指导研究生', '指导学生', '访问学者']
                }
                
                current_section = None
                temp_sections = {k: [] for k in sections_map.keys()}
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 检查是否是标题行
                    is_header = False
                    for section_key, keywords in sections_map.items():
                        for kw in keywords:
                            if kw in line and len(line) < 30: # 放宽长度限制
                                current_section = section_key
                                is_header = True
                                break
                        if is_header:
                            break
                    
                    if is_header:
                        continue
                    
                    if current_section:
                        if "版权所有" in line or "地址：" in line:
                            continue
                        temp_sections[current_section].append(line)
                    else:
                        # 尝试捕获简介 (如果不在任何section中)
                        # 排除基本信息行
                        if not any(x in line for x in ["电话", "邮箱", "地址", "研究方向", "QQ", "主讲课程"]):
                             # 简单的启发式：如果包含"教授"或"毕业"等词，或者是较长的段落
                             if len(line) > 10 or "教授" in line:
                                 temp_sections['personal_introduction'].append(line)

                # 合并内容
                for key, content_list in temp_sections.items():
                    content = '\n'.join(content_list).strip()
                    if content:
                        if not teacher_info[key]:
                            teacher_info[key] = content
                        elif len(content) > len(teacher_info[key]): # 如果新提取的内容更丰富，则替换或追加
                             # 这里简单追加，避免覆盖正则提取的短句
                             if teacher_info[key] not in content:
                                 teacher_info[key] += '\n' + content

            # 清理数据
            for key in teacher_info:
                if isinstance(teacher_info[key], str):
                    teacher_info[key] = teacher_info[key].strip()
                    # 去除多余的空白
                    teacher_info[key] = re.sub(r'\n\s*\n', '\n', teacher_info[key])

            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
