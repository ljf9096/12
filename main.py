import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import List, Set, Dict, Tuple, DefaultDict
import opencc

class TVChannelProcessor:
    def __init__(self):
        self.timestart = datetime.now()
        self.combined_blacklist = set()
        self.channel_sources = defaultdict(list)  # 存储每个频道的源及其响应时间
        self.all_urls = set()
        
        # 初始化频道容器
        self.init_channel_containers()
        
    def init_channel_containers(self):
        # 主频道容器
        self.ys_lines = []  # 央视频道
        self.ws_lines = []  # 卫视频道
        self.ty_lines = []  # 体育频道
        # ... 其他频道容器初始化
        self.other_lines = []
        
        self.removal_list = ["「IPV4」","「IPV6」","[ipv6]","[ipv4]","_电信", "电信",
                           "（HD）","[超清]","高清","超清", "-HD","(HK)","AKtv","@",
                           "IPV6","🎞️","🎦"," ","[BD]","[VGA]","[HD]","[SD]",
                           "(1080p)","(720p)","(480p)"]

    def read_txt_to_array(self, file_name: str) -> List[str]:
        """读取文本文件到数组"""
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file.readlines()]
        except Exception as e:
            print(f"读取文件错误 {file_name}: {e}")
            return []

    def process_channel_line(self, line: str):
        """处理单行频道数据"""
        if not line or "#genre#" in line or "#EXTINF:" in line:
            return
            
        try:
            parts = line.split(',')
            if len(parts) == 3 and parts[0].endswith('ms'):
                # 格式: "200ms,频道名称,URL"
                time_ms = float(parts[0].replace('ms', ''))
                name = parts[1].strip()
                url = parts[2].strip()
            elif len(parts) >= 2:
                # 格式: "频道名称,URL"
                time_ms = float('inf')  # 无响应时间数据
                name = parts[0].strip()
                url = parts[1].strip()
            else:
                return
                
            # 清理频道名称
            name = self.clean_channel_name(name)
            url = self.clean_url(url)
            
            if url and url not in self.combined_blacklist and url not in self.all_urls:
                self.all_urls.add(url)
                self.channel_sources[name].append((time_ms, url))
                
        except Exception as e:
            print(f"处理频道行错误: {e}")

    def clean_channel_name(self, name: str) -> str:
        """清理频道名称"""
        for pattern in self.removal_list:
            name = name.replace(pattern, "")
            
        replacements = {
            "CCTV-": "CCTV", "CCTV0": "CCTV",
            "PLUS": "+", "NewTV-": "NewTV",
            "iHOT-": "iHOT", "NEW": "New",
            "New_": "New"
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
            
        return name.strip()

    def clean_url(self, url: str) -> str:
        """清理URL"""
        return url.split('$')[0].strip()

    def select_top_sources(self, top_n=5):
        """选择每个频道响应时间最快的前N个源"""
        for name, sources in self.channel_sources.items():
            # 按响应时间排序 (从小到大)
            sorted_sources = sorted(sources, key=lambda x: x[0])
            # 取前N个
            top_sources = sorted_sources[:top_n]
            
            # 添加到对应分类
            for _, url in top_sources:
                line = f"{name},{url}"
                self.categorize_channel(name, line)

    def categorize_channel(self, name: str, line: str):
        """频道分类逻辑"""
        # 这里应该有实际的分类逻辑，简化版直接放入other
        self.other_lines.append(line)

    def generate_output(self):
        """生成输出内容"""
        utc_time = datetime.now(timezone.utc)
        beijing_time = utc_time + timedelta(hours=8)
        version = beijing_time.strftime("%Y%m%d %H:%M")
        
        output_lines = [
            f"更新时间,#genre#\n{version}\n",
            "央视频道,#genre#"
        ]
        
        # 添加各分类频道
        if self.ys_lines:
            output_lines.extend(self.ys_lines)
            
        output_lines.append("\n卫视频道,#genre#")
        if self.ws_lines:
            output_lines.extend(self.ws_lines)
            
        # 添加其他频道
        if self.other_lines:
            output_lines.append("\n其他频道,#genre#")
            output_lines.extend(self.other_lines)
            
        return '\n'.join(output_lines)

    def make_m3u(self, txt_content: str, m3u_file: str):
        """从文本内容生成M3U文件"""
        try:
            output = '#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml.gz"\n'
            group = ""
            
            for line in txt_content.split('\n'):
                if not line or line.startswith("更新时间,#genre#"):
                    continue
                    
                if "#genre#" in line:
                    group = line.split(',')[0]
                    output += f'#EXTINF:-1 group-title="{group}",\n'
                else:
                    name, url = line.split(',', 1)
                    logo = f"https://epg.112114.xyz/logo/{name}.png"
                    output += f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n'
                    output += f"{url}\n"
            
            with open(m3u_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"M3U文件已生成: {m3u_file}")
                
        except Exception as e:
            print(f"生成M3U文件错误: {e}")

    def run(self):
        """主运行方法"""
        # 加载黑名单
        blacklist = self.read_txt_to_array('blacklist_auto.txt')
        self.combined_blacklist = set(blacklist)
        
        # 加载白名单并处理
        whitelist = self.read_txt_to_array('whitelist_auto.txt')
        for line in whitelist:
            self.process_channel_line(line)
            
        # 处理URL源
        urls = self.read_txt_to_array('urls.txt')
        for url in urls:
            if url.startswith('http'):
                self.process_url(url)
                
        # 选择最佳源
        self.select_top_sources()
        
        # 生成输出文件
        output_content = self.generate_output()
        with open("live.txt", 'w', encoding='utf-8') as f:
            f.write(output_content)
            
        # 生成M3U文件
        self.make_m3u(output_content, "live.m3u")
        
        # 打印统计信息
        total_channels = len(self.channel_sources)
        total_sources = sum(len(sources) for sources in self.channel_sources.values())
        print(f"处理完成，共收集 {total_channels} 个频道，{total_sources} 个直播源")

    def process_url(self, url: str):
        """处理URL获取直播源"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
                for line in content.splitlines():
                    self.process_channel_line(line)
                    
        except Exception as e:
            print(f"处理URL错误 {url}: {e}")

if __name__ == "__main__":
    processor = TVChannelProcessor()
    processor.run()
