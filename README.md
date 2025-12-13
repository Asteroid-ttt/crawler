# 武汉大学多学院教师信息爬虫系统

## 项目概述

这是一个可扩展的教师信息爬虫系统，专门用于爬取武汉大学各学院的教师信息。系统采用模块化设计，支持多学院并发爬取、数据合并和多格式输出。

## 功能特性

- 🏫 **多学院支持**: 可配置化爬取不同学院的教师信息
- 🔄 **并发爬取**: 支持多线程并发爬取，提高效率
- 📊 **数据管理**: 统一的数据格式，支持去重和合并
- 💾 **多格式输出**: 支持JSON、CSV、Excel格式输出
- 🔧 **可扩展性**: 易于添加新学院的爬虫配置
- 📈 **统计分析**: 自动生成爬取统计和数据质量报告
- 🛡️ **错误处理**: 完善的重试机制和错误处理

## 项目架构

```
crawler/
├── config/                 # 配置文件目录
│   └── colleges.yaml      # 学院配置（YAML格式）
├── crawlers/               # 爬虫模块目录
│   ├── __init__.py        # 包初始化文件
│   ├── base_crawler.py    # 基础爬虫抽象类
│   ├── generic_crawler.py # 通用爬虫实现
│   ├── eis_crawler.py     # 电子信息学院爬虫
│   ├── cs_crawler.py      # 计算机学院爬虫
│   ├── jszy_crawler.py    # 教师主页系统爬虫
│   └── ...                # 其他学院爬虫
├── data/                   # 数据存储目录
│   ├── raw/               # 原始爬取数据
│   ├── processed/         # 处理后的数据
│   ├── colleges/          # 按学院分类的数据
│   ├── reports/           # 统计与质量报告
│   └── backup/            # 自动备份数据
├── crawler_manager.py      # 主控制器与调度器
├── data_manager.py         # 数据管理与持久化
├── main.py                # 主程序入口
├── pyproject.toml         # 项目依赖配置
└── README.md              # 项目文档
```

## 快速开始

### 1. 环境准备

**Python 版本要求**: Python 3.9+

**安装依赖**:
```powershell
# 方式1: 使用 pyproject.toml（推荐）
pip install -e .

# 方式2: 手动安装
pip install beautifulsoup4 requests pandas openpyxl pyyaml
```

### 2. 运行爬虫

```powershell
# 运行主程序
python .\main.py
```

**配置选择**:
- 编辑 `main.py` 中的 `target_colleges` 变量选择要爬取的学院
- 或修改为 `None` 爬取所有配置的学院

### 3. 配置学院

编辑 `config/colleges.yaml` 文件来配置要爬取的学院：

```yaml
colleges:
  eis:
    name: "电子信息学院"
    base_url: "http://eis.whu.edu.cn"
    teacher_list_url: "http://eis.whu.edu.cn/..."
    parser_class: "EISTeacherCrawler"
```

### 4. 查看结果

爬取结果将保存在 `data/` 目录下的不同子目录中：

#### 数据分类
- `data/raw/{college_code}/` - 各学院原始爬取数据
- `data/processed/merged/` - 合并处理后的数据
- `data/colleges/` - 按学院分类的最终数据
- `data/reports/` - 统计报告和数据质量分析
- `data/backup/` - 自动备份数据

#### 主要文件
- `all_colleges_teachers_YYYYMMDD_HHMMSS.json` - JSON格式合并数据
- `all_colleges_teachers_YYYYMMDD_HHMMSS.csv` - CSV格式合并数据  
- `all_colleges_teachers_YYYYMMDD_HHMMSS.xlsx` - Excel格式合并数据
- `statistics_YYYYMMDD_HHMMSS.json` - 统计报告
- `quality_report_YYYYMMDD_HHMMSS.json` - 数据质量报告

## 添加新学院

### 方法1: 创建专用爬虫（推荐）

1. 在 `crawlers/` 目录下创建新的爬虫文件
2. 继承 `BaseTeacherCrawler` 类
3. 实现必要的方法
4. 在配置文件中指定新的爬虫类

### 方法2: 使用通用爬虫

1. 在配置文件中添加学院信息
2. 设置 `parser_class` 为 `GenericTeacherCrawler`
3. 配置页面结构选择器

## 调试与测试

### 测试单个学院

```python
from crawler_manager import CrawlerManager

manager = CrawlerManager()

# 测试学院配置
result = manager.test_college_crawler('eis')
print(result)

# 测试特定教师页面
result = manager.test_college_crawler('pmc', 'https://pmc.whu.edu.cn/info/1025/165021.htm')
print(result)
```

### 从URL直接爬取

```python
# 自动检测并爬取任意教师页面
data = manager.crawl_from_url('https://jszy.whu.edu.cn/...')
```

## 使用示例

```python
from crawler_manager import CrawlerManager

# 创建管理器
manager = CrawlerManager()

# 查看可用学院
colleges = manager.get_available_colleges()
print("可用学院:", colleges)

# 爬取指定学院
target_colleges = ['eis', 'cs']  
data = manager.crawl_and_merge(college_list=target_colleges)

# 爬取所有学院
all_data = manager.crawl_and_merge()
```

## 常见问题

**Q: 爬取失败怎么办？**
A: 检查网络连接，查看 `config/colleges.yaml` 中的URL是否有效，或使用测试功能调试。

**Q: 如何添加新学院？**
A: 参考下面的"添加新学院"部分，或使用通用爬虫配置页面选择器。

**Q: 数据保存在哪里？**
A: 查看 `data/colleges/` 目录下的CSV和JSON文件，以及 `data/reports/` 下的统计报告。

## 许可证

MIT License