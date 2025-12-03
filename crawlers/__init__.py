"""
教师爬虫包
包含不同学院的教师信息爬虫类
"""

from .base_crawler import BaseTeacherCrawler, load_config
from .eis_crawler import EISTeacherCrawler
from .cs_crawler import CSTeacherCrawler
from .generic_crawler import (
    GenericTeacherCrawler, 
    MathsTeacherCrawler,
    CRAWLER_CLASSES
)

__all__ = [
    'BaseTeacherCrawler',
    'EISTeacherCrawler', 
    'CSTeacherCrawler',
    'GenericTeacherCrawler',
    'MathsTeacherCrawler',
    'CRAWLER_CLASSES',
    'load_config'
]