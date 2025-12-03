import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"}

for start in range(0, 250, 25):

    response = requests.get(url=f"https://movie.douban.com/top250?start={start}", headers=headers)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    all_titles = soup.find_all("span", attrs={"class": "title"})

    for title in all_titles:
        string_title = title.string
        if "/" not in string_title:
            print(string_title)