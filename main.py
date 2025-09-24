import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import List, Set, Dict, Tuple
import opencc

class TVChannelProcessor:
    def __init__(self):
        self.timestart = datetime.now()
        self.combined_blacklist = set()
        self.all_urls = set()
        self.channel_sources = defaultdict(list)  # 存储频道源及其响应时间
        
        # 初始化频道容器
        self.ys_lines = []  # 央视频道
        self.ws_lines = []  # 卫视频道
        self.newtv_lines = []  # NewTV频道
        
        self.removal_list = ["「IPV4」","「IPV6」","[ipv6]","[ipv4]","_电信", "电信",
                           "（HD）","[超清]","高清","超清", "-HD","(HK)","AKtv","@",
                           "IPV6","🎞️","🎦"," ","[BD]","[VGA]","[HD]","[SD]",
                           "(1080p)","(720p)","(480p)"]

    def read_txt_to_array(self, file_name: str) -> List[str]:
        """读取文本文件到数组"""
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(f"读取文件错误 {file_name}: {e}")
            return []

    def load_corrections_name(self, filename: str) -> Dict[str, str]:
        """加载频道名称修正"""
        corrections = {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            correct_name = parts[0]
                            for name in parts[1:]:
                                corrections[name] = correct_name
        except Exception as e:
            print(f"加载修正文件错误: {e}")
        return corrections

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

    def add_channel_source(self, name: str, url: str, response_time: float = 9999.0):
        """添加频道源，每个频道最多保留5个最快的源"""
        if not url or url in self.combined_blacklist or url in self.all_urls:
            return
            
        self.all_urls.add(url)
        self.channel_sources[name].append((response_time, url))
        
        # 按响应时间排序并保留前5个
        self.channel_sources[name].sort(key=lambda x: x[0])
        if len(self.channel_sources[name]) > 5:
            self.channel_sources[name] = self.channel_sources[name][:5]

    def process_line(self, line: str):
        """处理单行数据"""
        if "#genre#" in line or "#EXTINF:" in line or "://" not in line:
            return
            
        try:
            # 处理普通行 (频道名称,URL)
            if line.count(',') == 1:
                name, url = line.split(',', 1)
                self.add_channel_source(
                    self.clean_channel_name(name.strip()),
                    self.clean_url(url.strip())
                )
            # 处理带响应时间的行 (响应时间,频道名称,URL)
            elif line.count(',') >= 2:
                parts = line.split(',', 2)
                try:
                    time_ms = float(parts[0].replace("ms", "").strip())
                    if time_ms < 2000:  # 只保留2秒内的源
                        self.add_channel_source(
                            self.clean_channel_name(parts[1].strip()),
                            self.clean_url(parts[2].strip()),
                            time_ms
                        )
                except ValueError:
                    pass
                    
        except Exception as e:
            print(f"处理行错误: {line}, 错误: {e}")

    def download_and_process(self, url: str):
        """下载并处理URL内容"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                
                # 尝试不同编码
                for encoding in ['utf-8', 'gbk', 'gb2312']:
                    try:
                        text = content.decode(encoding)
                        # 处理M3U格式
                        if text.strip().startswith("#EXTM3U"):
                            text = self.convert_m3u_to_txt(text)
                        
                        # 处理每一行
                        for line in text.splitlines():
                            self.process_line(line.strip())
                        break
                    except UnicodeDecodeError:
                        continue
                        
        except Exception as e:
            print(f"处理URL错误 {url}: {e}")

    def convert_m3u_to_txt(self, m3u_content: str) -> str:
        """转换M3U为TXT格式"""
        lines = []
        current_name = ""
        
        for line in m3u_content.split('\n'):
            line = line.strip()
            if line.startswith("#EXTINF"):
                parts = line.split(',', 1)
                if len(parts) > 1:
                    current_name = parts[1]
            elif line.startswith(("http://", "https://", "rtmp://")):
                if current_name:
                    lines.append(f"{current_name},{line}")
                    current_name = ""
        
        return '\n'.join(lines)

    def categorize_channels(self):
        """将频道分类"""
        for name, sources in self.channel_sources.items():
            # 已经按响应时间排序，直接取前5个
            for time_ms, url in sources[:5]:
                line = f"{name},{url}"
                
                if "CCTV" in name or "央视" in name:
                    self.ys_lines.append(line)
                elif "卫视" in name:
                    self.ws_lines.append(line)
                elif "NewTV" in name.upper():
                    self.newtv_lines.append(line)

    def generate_live_txt(self):
        """生成live.txt文件"""
        beijing_time = datetime.now(timezone.utc) + timedelta(hours=8)
        version = beijing_time.strftime("%Y%m%d %H:%M")
        
        content = [
            "更新时间,#genre#",
            version,
            "",
            "央视频道,#genre#",
            *self.ys_lines,
            "",
            "卫视频道,#genre#",
            *self.ws_lines,
            "",
            "NewTV频道,#genre#",
            *self.newtv_lines
        ]
        
        try:
            with open("live.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            print("live.txt 生成成功")
        except Exception as e:
            print(f"写入live.txt错误: {e}")

    def generate_m3u(self):
        """生成M3U文件"""
        try:
            m3u_content = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml.gz"']
            current_group = ""
            
            with open("live.txt", 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.endswith("#genre#"):
                        current_group = line.replace(",#genre#", "")
                    elif ',' in line:
                        name, url = line.split(',', 1)
                        logo = f"https://epg.112114.xyz/logo/{name}.png"
                        m3u_content.extend([
                            f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{current_group}",{name}',
                            url
                        ])
            
            with open("live.m3u", 'w', encoding='utf-8') as f:
                f.write('\n'.join(m3u_content))
            print("live.m3u 生成成功")
            
        except Exception as e:
            print(f"生成M3U文件错误: {e}")

    def run(self):
        """主运行函数"""
        print("开始处理电视频道...")
        print("配置: 只保留央视频道、卫视频道、NewTV频道")
        print("每个频道只保留响应时间最快的前5个源")
        
        # 加载黑名单
        self.combined_blacklist = set(self.read_txt_to_array('blacklist_auto.txt'))
        
        # 加载白名单并处理
        for line in self.read_txt_to_array('whitelist_auto.txt'):
            self.process_line(line)
        
        # 处理URL列表
        for url in self.read_txt_to_array('urls.txt'):
            if url.startswith('http'):
                self.download_and_process(url)
        
        # 分类频道
        self.categorize_channels()
        
        # 生成输出文件
        self.generate_live_txt()
        self.generate_m3u()
        
        # 打印统计信息
        timeend = datetime.now()
        elapsed = timeend - self.timestart
        print(f"\n处理完成，耗时: {elapsed.total_seconds():.1f}秒")
        print(f"央视频道: {len(self.ys_lines)}")
        print(f"卫视频道: {len(self.ws_lines)}")
        print(f"NewTV频道: {len(self.newtv_lines)}")
        print(f"总频道数: {len(self.ys_lines) + len(self.ws_lines) + len(self.newtv_lines)}")

if __name__ == "__main__":
    TVChannelProcessor().run()
