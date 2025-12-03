"""
基础爬虫类 - 提供通用的爬虫功能
"""
import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from urllib.parse import urljoin
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
import yaml

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseTeacherCrawler(ABC):
    """教师爬虫基类"""
    
    def __init__(self, college_config):
        """
        初始化爬虫
        
        Args:
            college_config (dict): 学院配置信息
        """
        self.config = college_config
        self.base_url = college_config['base_url']
        self.main_url = college_config['teacher_list_url']
        self.detail_pattern = college_config['teacher_detail_pattern']
        self.encoding = college_config.get('encoding', 'utf-8')
        
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
        
        # 全局配置
        self.delay = college_config.get('delay', 1)
        self.timeout = college_config.get('timeout', 10)
        self.retry_times = college_config.get('retry_times', 3)
        
    def make_request(self, url, retries=None):
        """
        发送HTTP请求，带重试机制
        
        Args:
            url (str): 请求URL
            retries (int): 重试次数，默认使用配置值
            
        Returns:
            requests.Response: 响应对象，失败返回None
        """
        if retries is None:
            retries = self.retry_times
            
        for attempt in range(retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = self.encoding
                return response
            except requests.RequestException as e:
                if attempt < retries:
                    logger.warning(f"请求失败 (尝试 {attempt + 1}/{retries + 1}): {e}")
                    time.sleep(self.delay * (attempt + 1))  # 递增延时
                else:
                    logger.error(f"请求最终失败 {url}: {e}")
                    return None
    
    @abstractmethod
    def get_teacher_links(self):
        """
        获取所有教师的详情页面链接
        每个子类需要实现此方法，因为不同学院的页面结构不同
        
        Returns:
            list: 教师详情页面链接列表
        """
        pass
    
    @abstractmethod
    def parse_teacher_info(self, url):
        """
        解析单个教师的详情信息
        每个子类需要实现此方法，因为不同学院的页面结构不同
        
        Args:
            url (str): 教师详情页面URL
            
        Returns:
            dict: 教师信息字典，失败返回None
        """
        pass
    
    def extract_text_by_pattern(self, soup, pattern_dict):
        """
        通用文本提取方法
        
        Args:
            soup (BeautifulSoup): 页面解析对象
            pattern_dict (dict): 提取模式字典
                {
                    'field_name': {
                        'selector': 'css选择器',
                        'attr': '属性名(可选)',
                        'prefix': '前缀(可选)',
                        'clean': True/False (是否清理文本)
                    }
                }
        
        Returns:
            dict: 提取的数据字典
        """
        result = {}
        
        for field_name, pattern in pattern_dict.items():
            try:
                element = soup.select_one(pattern['selector'])
                if element:
                    if 'attr' in pattern:
                        text = element.get(pattern['attr'], '')
                    else:
                        text = element.get_text(strip=True)
                    
                    if pattern.get('prefix'):
                        text = text.replace(pattern['prefix'], '').strip()
                    
                    if pattern.get('clean', True):
                        text = self.clean_text(text)
                    
                    result[field_name] = text
                else:
                    result[field_name] = ''
            except Exception as e:
                logger.warning(f"提取字段 {field_name} 失败: {e}")
                result[field_name] = ''
        
        return result
    
    def clean_text(self, text):
        """
        清理文本内容
        
        Args:
            text (str): 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ''
        
        # 替换HTML实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        # 清理空白字符
        text = re.sub(r'[ \t]+', ' ', text)  # 合并空格和制表符
        text = re.sub(r'\n+', ' ', text)     # 合并换行符
        
        return text.strip()
    
    def save_to_json(self, teachers_data, filename=None):
        """保存数据到JSON文件"""
        if filename is None:
            filename = f"{self.config['name']}_teachers.json"
            
        try:
            # 确保colleges目录存在
            data_dir = Path(self.config.get('data_dir', 'data'))
            colleges_dir = data_dir / 'colleges'
            colleges_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = colleges_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(teachers_data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到 {filepath}")
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def save_to_csv(self, teachers_data, filename=None):
        """保存数据到CSV文件"""
        if filename is None:
            filename = f"{self.config['name']}_teachers.csv"
            
        try:
            if not teachers_data:
                return
                
            # 确保colleges目录存在
            data_dir = Path(self.config.get('data_dir', 'data'))
            colleges_dir = data_dir / 'colleges'
            colleges_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = colleges_dir / filename
            fieldnames = list(teachers_data[0].keys())
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for teacher in teachers_data:
                    writer.writerow(teacher)
            logger.info(f"数据已保存到 {filepath}")
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
    
    def crawl_all_teachers(self):
        """爬取所有教师信息的主函数"""
        logger.info(f"开始爬取 {self.config['name']} 教师信息...")
        
        # 获取所有教师链接
        teacher_links = self.get_teacher_links()
        
        if not teacher_links:
            logger.warning("未找到教师链接，请检查页面结构")
            return []
        
        # 解析每个教师的信息
        teachers_data = []
        for i, link in enumerate(teacher_links, 1):
            logger.info(f"处理第 {i}/{len(teacher_links)} 个教师")
            
            teacher_info = self.parse_teacher_info(link)
            if teacher_info:
                # 添加学院信息
                teacher_info['college'] = self.config['name']
                teachers_data.append(teacher_info)
            
            # 延时避免过于频繁的请求
            if i < len(teacher_links):
                time.sleep(self.delay)
        
        # 保存数据
        if teachers_data:
            self.save_to_json(teachers_data)
            self.save_to_csv(teachers_data)
            logger.info(f"爬取完成！共获取 {len(teachers_data)} 位 {self.config['name']} 教师信息")
        else:
            logger.warning("未获取到任何教师信息")
        
        return teachers_data

def load_config(config_path='config/colleges.yaml'):
    """
    加载配置文件
    
    Args:
        config_path (str): 配置文件路径
        
    Returns:
        dict: 配置字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None