"""
对比遥感学院和计算机学院列表页面的源码结构
"""
import requests
from bs4 import BeautifulSoup

def analyze_college_pages():
    """分析学院页面的链接结构"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    colleges = {
        "遥感信息工程学院": "https://rsgis.whu.edu.cn/szdw4/zrjs.htm",
        "计算机学院": "https://cs.whu.edu.cn/szdw/zrjs.htm"
    }
    
    for college_name, url in colleges.items():
        print(f"\n{'='*50}")
        print(f"分析 {college_name}")
        print(f"URL: {url}")
        print(f"{'='*50}")
        
        try:
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"❌ 无法访问页面 (状态码: {response.status_code})")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            
            # 分类链接
            jszy_links = []
            college_links = []
            other_links = []
            
            for link in links:
                href = link.get('href', '').strip()
                text = link.get_text().strip()
                
                # 跳过空链接和无关链接
                if not href or href in ['#', '/', 'javascript:void(0)']:
                    continue
                
                # 补全相对链接
                if href.startswith('/'):
                    if 'cs.whu.edu.cn' in url:
                        href = 'https://cs.whu.edu.cn' + href
                    elif 'rsgis.whu.edu.cn' in url:
                        href = 'https://rsgis.whu.edu.cn' + href
                elif not href.startswith('http'):
                    continue
                
                # 分类链接
                if 'jszy.whu.edu.cn' in href:
                    jszy_links.append((text, href))
                elif college_name == "遥感信息工程学院" and 'rsgis.whu.edu.cn' in href and '/info/1004/' in href:
                    college_links.append((text, href))
                elif college_name == "计算机学院" and 'cs.whu.edu.cn' in href and '/info/1019/' in href:
                    college_links.append((text, href))
                elif any(keyword in href for keyword in ['/info/', '/teacher', '/faculty']):
                    other_links.append((text, href))
            
            print(f"JSZY链接: {len(jszy_links)} 个")
            if jszy_links:
                for i, (text, href) in enumerate(jszy_links[:5], 1):
                    print(f"  {i}. {text} -> {href}")
                if len(jszy_links) > 5:
                    print(f"  ... (还有 {len(jszy_links) - 5} 个)")
            
            print(f"\n学院域名链接: {len(college_links)} 个")
            if college_links:
                for i, (text, href) in enumerate(college_links[:5], 1):
                    print(f"  {i}. {text} -> {href}")
                if len(college_links) > 5:
                    print(f"  ... (还有 {len(college_links) - 5} 个)")
            
            print(f"\n其他可能的教师链接: {len(other_links)} 个")
            if other_links:
                for i, (text, href) in enumerate(other_links[:3], 1):
                    print(f"  {i}. {text} -> {href}")
            
            # 分析HTML结构中的特殊内容
            print(f"\n页面结构分析:")
            
            # 查找包含"jszy"的文本
            jszy_mentions = soup.find_all(text=lambda text: text and 'jszy' in text.lower())
            if jszy_mentions:
                print(f"  页面中提到'jszy': {len(jszy_mentions)} 处")
                for mention in jszy_mentions[:3]:
                    print(f"    - {mention.strip()[:100]}")
            
            # 查找iframe或其他嵌入内容
            iframes = soup.find_all('iframe')
            if iframes:
                print(f"  iframe元素: {len(iframes)} 个")
                for iframe in iframes:
                    src = iframe.get('src', '')
                    if src:
                        print(f"    - {src}")
                        
        except Exception as e:
            print(f"❌ 分析失败: {e}")

if __name__ == "__main__":
    analyze_college_pages()