import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc
from typing import List, Set, Dict, Tuple
from collections import defaultdict

class TVChannelProcessor:
    def __init__(self):
        self.timestart = datetime.now()
        self.combined_blacklist = set()
        self.all_urls = set()
        
        # 初始化频道容器 - 只保留三个分类
        self.ys_lines = []  # 央视频道
        self.ws_lines = []  # 卫视频道
        self.newtv_lines = []  # NewTV频道
        
        # 存储每个频道的URL和响应时间
        self.channel_data = defaultdict(list)
        
        self.removal_list = ["「IPV4」","「IPV6」","[ipv6]","[ipv4]","_电信", "电信","（HD）","[超清]","高清","超清", "-HD","(HK)","AKtv","@","IPV6","🎞️","🎦"," ","[BD]","[VGA]","[HD]","[SD]","(1080p)","(720p)","(480p)"]

    def read_txt_to_array(self, file_name: str) -> List[str]:
        """读取文本文件到数组"""
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"文件未找到: {file_name}")
            return []
        except Exception as e:
            print(f"读取文件错误 {file_name}: {e}")
            return []

    def read_blacklist_from_txt(self, file_path: str) -> List[str]:
        """读取黑名单"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return [line.split(',')[1].strip() for line in file if ',' in line]
        except Exception as e:
            print(f"读取黑名单错误 {file_path}: {e}")
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

    def traditional_to_simplified(self, text: str) -> str:
        """繁体转简体"""
        try:
            converter = opencc.OpenCC('t2s')
            return converter.convert(text)
        except Exception as e:
            print(f"繁简转换错误: {e}")
            return text

    def clean_channel_name(self, channel_name: str) -> str:
        """清理频道名称"""
        for item in self.removal_list:
            channel_name = channel_name.replace(item, "")
        
        replacements = {
            "CCTV-": "CCTV",
            "CCTV0": "CCTV",
            "PLUS": "+",
            "NewTV-": "NewTV",
            "iHOT-": "iHOT",
            "NEW": "New",
            "New_": "New"
        }
        
        for old, new in replacements.items():
            channel_name = channel_name.replace(old, new)
            
        return channel_name.strip()

    def clean_url(self, url: str) -> str:
        """清理URL"""
        last_dollar_index = url.rfind('$')
        return url[:last_dollar_index] if last_dollar_index != -1 else url

    def add_channel_url(self, channel_name: str, channel_url: str, response_time: float = 9999.0):
        """添加频道URL到对应分类，只保留最快的前5个"""
        if not channel_url or channel_url in self.combined_blacklist:
            return
            
        # 如果URL已存在，跳过
        if channel_url in self.all_urls:
            return
            
        self.all_urls.add(channel_url)
        
        # 存储频道数据，包含响应时间
        self.channel_data[channel_name].append((response_time, channel_url))
        
        # 每个频道只保留最快的前5个URL
        if len(self.channel_data[channel_name]) > 5:
            # 按响应时间排序，保留最快的5个
            self.channel_data[channel_name].sort(key=lambda x: x[0])
            self.channel_data[channel_name] = self.channel_data[channel_name][:5]

    def process_line(self, line: str):
        """处理单行数据"""
        if "#genre#" in line or "#EXTINF:" in line or "://" not in line:
            return
            
        try:
            parts = line.split(',', 1)
            if len(parts) != 2:
                return
                
            channel_name, channel_url = parts
            channel_name = self.traditional_to_simplified(channel_name)
            channel_name = self.clean_channel_name(channel_name)
            channel_name = self.corrections_name.get(channel_name, channel_name)
            
            channel_url = self.clean_url(channel_url.strip())
            
            # 处理包含多个URL的情况
            if '#' in channel_url:
                urls = channel_url.split('#')
                for url in urls:
                    if url.strip() and '://' in url:
                        self.add_channel_url(channel_name, url.strip())
            else:
                if channel_url.strip() and '://' in channel_url:
                    self.add_channel_url(channel_name, channel_url.strip())
                    
        except Exception as e:
            print(f"处理行错误: {line}, 错误: {e}")

    def process_whitelist_line(self, line: str):
        """处理白名单行（包含响应时间）"""
        if "#genre#" in line or "://" not in line:
            return
            
        try:
            # 白名单格式: 响应时间,频道名称,URL
            parts = line.split(',', 2)
            if len(parts) == 3:
                response_time_str, channel_name, channel_url = parts
                try:
                    response_time = float(response_time_str.replace("ms", "").strip())
                    if response_time >= 2000:  # 超过2秒的跳过
                        return
                except ValueError:
                    response_time = 9999.0
                
                channel_name = self.traditional_to_simplified(channel_name)
                channel_name = self.clean_channel_name(channel_name)
                channel_name = self.corrections_name.get(channel_name, channel_name)
                
                channel_url = self.clean_url(channel_url.strip())
                
                if channel_url and '://' in channel_url:
                    self.add_channel_url(channel_name, channel_url, response_time)
                    
        except Exception as e:
            print(f"处理白名单行错误: {line}, 错误: {e}")

    def download_and_process_url(self, url: str):
        """下载并处理URL内容"""
        print(f"处理URL: {url}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                
                # 尝试不同编码
                encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']
                text = None
                
                for encoding in encodings:
                    try:
                        text = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if text is None:
                    print(f"无法解码内容: {url}")
                    return
                
                # 处理M3U格式
                if text.strip().startswith("#EXTM3U"):
                    text = self.convert_m3u_to_txt(text)
                
                # 处理每一行
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        self.process_line(line)
                        
        except Exception as e:
            print(f"处理URL错误 {url}: {e}")

    def convert_m3u_to_txt(self, m3u_content: str) -> str:
        """转换M3U格式为TXT格式"""
        lines = m3u_content.split('\n')
        result = []
        current_name = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # 提取频道名称
                parts = line.split(',', 1)
                if len(parts) > 1:
                    current_name = parts[1]
            elif line.startswith(("http://", "https://", "rtmp://", "rtsp://")):
                if current_name:
                    result.append(f"{current_name},{line}")
                    current_name = ""
        
        return '\n'.join(result)

    def is_ys_channel(self, channel_name: str) -> bool:
        """判断是否为央视频道"""
        ys_keywords = ['CCTV', '央视', '中央']
        return any(keyword in channel_name for keyword in ys_keywords)

    def is_ws_channel(self, channel_name: str) -> bool:
        """判断是否为卫视频道"""
        ws_keywords = [
            '卫视', '湖南', '浙江', '江苏', '北京', '东方', '广东', '深圳', 
            '天津', '重庆', '山东', '湖北', '四川', '辽宁', '河南', '安徽',
            '河北', '福建', '江西', '广西', '贵州', '黑龙江', '吉林', '山西',
            '陕西', '云南', '海南', '甘肃', '宁夏', '青海', '西藏', '新疆',
            '内蒙古', '凤凰', '翡翠'
        ]
        return any(keyword in channel_name for keyword in ws_keywords)

    def is_newtv_channel(self, channel_name: str) -> bool:
        """判断是否为NewTV频道"""
        newtv_keywords = ['NewTV', 'New TV', 'NEWTV']
        return any(keyword.upper() in channel_name.upper() for keyword in newtv_keywords)

    def categorize_channels(self):
        """将频道分类到对应的容器中"""
        for channel_name, url_list in self.channel_data.items():
            # 按响应时间排序，取最快的前5个
            url_list.sort(key=lambda x: x[0])
            
            for response_time, url in url_list[:5]:
                line = f"{channel_name},{url}"
                
                # 分类逻辑 - 只保留三个分类
                if self.is_ys_channel(channel_name):
                    self.ys_lines.append(line)
                elif self.is_ws_channel(channel_name):
                    self.ws_lines.append(line)
                elif self.is_newtv_channel(channel_name):
                    self.newtv_lines.append(line)
                # 其他频道直接忽略，不添加到任何分类

    def generate_output_files(self):
        """生成输出文件"""
        # 获取当前时间
        beijing_time = datetime.now(timezone.utc) + timedelta(hours=8)
        formatted_time = beijing_time.strftime("%Y%m%d %H:%M")
        
        # 构建live.txt内容
        content_lines = []
        content_lines.append("更新时间,#genre#")
        content_lines.append(formatted_time)
        content_lines.append("")
        
        # 添加三个分类
        categories = [
            ("央视频道,#genre#", self.ys_lines),
            ("卫视频道,#genre#", self.ws_lines),
            ("NewTV频道,#genre#", self.newtv_lines),
        ]
        
        for category_name, lines in categories:
            if lines:  # 只添加有内容的分类
                content_lines.append(category_name)
                content_lines.extend(lines)
                content_lines.append("")
        
        # 写入live.txt
        try:
            with open("live.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content_lines))
            print("live.txt 生成成功")
            print(f"央视频道数量: {len(self.ys_lines)}")
            print(f"卫视频道数量: {len(self.ws_lines)}")
            print(f"NewTV频道数量: {len(self.newtv_lines)}")
        except Exception as e:
            print(f"写入live.txt错误: {e}")

    def make_m3u(self, txt_file: str, m3u_file: str):
        """生成M3U文件"""
        try:
            m3u_content = ['#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml.gz"']
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                current_group = ""
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.endswith("#genre#"):
                        current_group = line.replace(",#genre#", "")
                    elif ',' in line and '://' in line:
                        channel_name, url = line.split(',', 1)
                        logo_url = f"https://epg.112114.xyz/logo/{channel_name}.png"
                        
                        m3u_content.append(f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{current_group}",{channel_name}')
                        m3u_content.append(url)
            
            with open(m3u_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(m3u_content))
                
            print(f"{m3u_file} 生成成功")
            
        except Exception as e:
            print(f"生成M3U文件错误: {e}")

    def run(self):
        """主运行函数"""
        print("开始处理电视频道...")
        print("只保留：央视频道、卫视频道、NewTV频道")
        print("每个频道只保留响应时间最快的前5个源")
        
        # 加载黑名单
        blacklist_auto = self.read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_auto.txt')
        blacklist_manual = self.read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_manual.txt')
        self.combined_blacklist = set(blacklist_auto + blacklist_manual)
        
        # 加载白名单
        whitelist_manual = self.read_txt_to_array('assets/whitelist-blacklist/whitelist_manual.txt')
        whitelist_auto = self.read_txt_to_array('assets/whitelist-blacklist/whitelist_auto.txt')
        
        # 加载名称修正
        self.corrections_name = self.load_corrections_name('assets/corrections_name.txt')
        
        # 处理手动白名单
        print("处理手动白名单...")
        for line in whitelist_manual:
            self.process_line(line)
        
        # 处理自动白名单（含响应时间）
        print("处理自动白名单...")
        for line in whitelist_auto:
            self.process_whitelist_line(line)
        
        # 处理URL列表
        urls = self.read_txt_to_array('assets/urls.txt')
        print(f"发现 {len(urls)} 个URL需要处理")
        
        for url in urls:
            if url.startswith('http'):
                self.download_and_process_url(url)
        
        # 分类频道
        print("分类频道...")
        self.categorize_channels()
        
        # 生成输出文件
        print("生成输出文件...")
        self.generate_output_files()
        self.make_m3u("live.txt", "live.m3u")
        
        # 打印统计信息
        self.print_statistics()

    def print_statistics(self):
        """打印统计信息"""
        timeend = datetime.now()
        elapsed = timeend - self.timestart
        total_seconds = elapsed.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        
        total_channels = len(self.ys_lines) + len(self.ws_lines) + len(self.newtv_lines)
        
        print(f"\n=== 处理完成 ===")
        print(f"执行时间: {minutes}分{seconds}秒")
        print(f"黑名单数量: {len(self.combined_blacklist)}")
        print(f"央视频道数: {len(self.ys_lines)}")
        print(f"卫视频道数: {len(self.ws_lines)}")
        print(f"NewTV频道数: {len(self.newtv_lines)}")
        print(f"总频道数: {total_channels}")
        print(f"每个频道保留最快的前5个源")

if __name__ == "__main__":
    processor = TVChannelProcessor()
    processor.run()
