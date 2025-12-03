import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from urllib.parse import urljoin
import logging
import re

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TeacherCrawler:
    def __init__(self):
        self.base_url = "http://eis.whu.edu.cn"
        self.main_url = "http://eis.whu.edu.cn/index/goSzdw?flag=1&newskind_id=20160320222026165YIdDsQIbgNtoE"
        self.session = requests.Session()
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_teacher_links(self):
        """获取所有教师的详情页面链接"""
        try:
            logger.info("开始获取教师列表页面...")
            response = self.session.get(self.main_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            teacher_links = []
            
            # 查找教师链接，根据实际页面结构调整选择器
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                # 筛选教师详情页面的链接 - 包含szdwDetail的链接
                if 'szdwDetail' in href:
                    # 处理&amp;转义字符
                    href = href.replace('&amp;', '&')
                    full_url = urljoin(self.base_url, href)
                    if full_url not in teacher_links:
                        teacher_name = link.get_text(strip=True)
                        teacher_links.append(full_url)
                        logger.info(f"找到教师链接: {teacher_name} - {full_url}")
            
            logger.info(f"共找到 {len(teacher_links)} 个教师链接")
            return teacher_links
            
        except requests.RequestException as e:
            logger.error(f"获取教师列表失败: {e}")
            return []
    
    def parse_teacher_info(self, url):
        """解析单个教师的详情信息"""
        try:
            logger.info(f"正在解析教师信息: {url}")
            time.sleep(1)  # 延时避免过于频繁的请求
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
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

            # 通用方法：根据h2标题提取对应的内容
            def extract_section_content(soup, section_title):
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
            
            # 提取个人简介
            teacher_info['personal_introduction'] = extract_section_content(soup, '个人简介')
            
            # 提取主讲课程
            teacher_info['courses_taught'] = extract_section_content(soup, '主讲课程')
            
            # 提取主要科研课题及项目
            teacher_info['research_projects'] = extract_section_content(soup, '主要科研课题及项目')
            
            # 提取指导学生情况
            teacher_info['student_guidance'] = extract_section_content(soup, '指导学生情况')
            
            logger.info(f"成功解析教师: {teacher_info['name']}")
            return teacher_info
            
        except requests.RequestException as e:
            logger.error(f"解析教师信息失败 {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"解析教师信息时发生错误 {url}: {e}")
            return None
    
    def save_to_json(self, teachers_data, filename='teachers.json'):
        """保存数据到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(teachers_data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def save_to_csv(self, teachers_data, filename='teachers.csv'):
        """保存数据到CSV文件"""
        try:
            if not teachers_data:
                return
                
            fieldnames = list(teachers_data[0].keys())
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for teacher in teachers_data:
                    writer.writerow(teacher)
            logger.info(f"数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def crawl_all_teachers(self):
        """爬取所有教师信息的主函数"""
        logger.info("开始爬取教师信息...")
        
        # 获取所有教师链接
        teacher_links = self.get_teacher_links()
        
        if not teacher_links:
            logger.warning("未找到教师链接，请检查页面结构")
            return
        
        # 解析每个教师的信息
        teachers_data = []
        for i, link in enumerate(teacher_links, 1):
            logger.info(f"处理第 {i}/{len(teacher_links)} 个教师")
            teacher_info = self.parse_teacher_info(link)
            if teacher_info:
                teachers_data.append(teacher_info)
        
        # 保存数据
        if teachers_data:
            self.save_to_json(teachers_data)
            self.save_to_csv(teachers_data)
            logger.info(f"爬取完成！共获取 {len(teachers_data)} 位教师信息")
        else:
            logger.warning("未获取到任何教师信息")

def main():
    crawler = TeacherCrawler()
    crawler.crawl_all_teachers()


def test_one():
    crawler = TeacherCrawler()
    test_url = "http://eis.whu.edu.cn/index/szdwDetail?rsh=00007285&newskind_id=20160320222150685844oLXklVFf7H"
    teacher_info = crawler.parse_teacher_info(test_url)
    if teacher_info:
        print(json.dumps(teacher_info, ensure_ascii=False, indent=2))
    else:
        print("Failed to parse teacher info.")

if __name__ == "__main__":
    main()