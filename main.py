import urllib.request
from urllib.parse import urlparse
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

class TVChannelProcessor:
    def __init__(self):
        self.timestart = datetime.now()
        self.blacklist = set()
        self.channel_sources = defaultdict(list)
        self.output_lines = []
        
        # 初始化频道容器
        self.channel_containers = {
            'ys': [], 'ws': [], 'ty': [], 'dy': [], 'dsj': [],
            'gat': [], 'twt': [], 'gj': [], 'jlp': [], 'xq': [],
            'js': [], 'newtv': [], 'ihot': [], 'et': [], 'zy': [],
            'mdd': [], 'yy': [], 'game': [], 'radio': [], 'zb': [],
            'cw': [], 'mtv': [], 'migu': [], 'other': []
        }
        
        self.removal_patterns = [
            "「IPV4」", "「IPV6」", "[ipv6]", "[ipv4]", "_电信", "电信",
            "（HD）", "[超清]", "高清", "超清", "-HD", "(HK)", "AKtv",
            "@", "IPV6", "🎞️", "🎦", " ", "[BD]", "[VGA]", "[HD]",
            "[SD]", "(1080p)", "(720p)", "(480p)"
        ]

    def load_file(self, file_path: str) -> List[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return []

    def process_channel(self, line: str):
        if not line or "#genre#" in line:
            return
            
        try:
            parts = line.split(',')
            if len(parts) == 3 and parts[0].endswith('ms'):
                time_ms = float(parts[0].replace('ms', ''))
                name = parts[1].strip()
                url = parts[2].strip()
            elif len(parts) >= 2:
                time_ms = float('inf')
                name = parts[0].strip()
                url = parts[1].strip()
            else:
                return
                
            # 清理频道名称
            for pattern in self.removal_patterns:
                name = name.replace(pattern, "")
                
            # 存储源信息
            if url not in self.blacklist:
                self.channel_sources[name].append((time_ms, url))
                
        except Exception as e:
            print(f"Error processing line: {e}")

    def select_top_sources(self, top_n=5):
        for name, sources in self.channel_sources.items():
            # 按响应时间排序并选择前N个
            sorted_sources = sorted(sources, key=lambda x: x[0])[:top_n]
            # 添加到对应分类
            container = self.get_channel_container(name)
            for _, url in sorted_sources:
                container.append(f"{name},{url}")

    def get_channel_container(self, name: str) -> List[str]:
        # 这里应该有实际的频道分类逻辑
        # 简化版直接放入other
        return self.channel_containers['other']

    def generate_output(self):
        utc_time = datetime.now(timezone.utc)
        beijing_time = utc_time + timedelta(hours=8)
        version = beijing_time.strftime("%Y%m%d %H:%M")
        
        self.output_lines.append(f"更新时间,#genre#\n{version}")
        
        # 添加各分类频道
        for category, lines in self.channel_containers.items():
            if lines:
                self.output_lines.append(f"\n{category},#genre#")
                self.output_lines.extend(lines)

    def save_to_file(self, filename="live.txt"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.output_lines))
            print(f"文件已保存: {filename}")
        except Exception as e:
            print(f"保存文件失败: {e}")

    def run(self):
        # 加载黑名单
        self.blacklist = set(self.load_file('blacklist_auto.txt'))
        
        # 加载白名单并处理
        whitelist = self.load_file('whitelist_auto.txt')
        for line in whitelist:
            self.process_channel(line)
            
        # 处理URL源
        urls = self.load_file('urls.txt')
        for url in urls:
            if url.startswith('http'):
                self.process_url(url)
                
        # 选择最佳源
        self.select_top_sources()
        
        # 生成输出
        self.generate_output()
        self.save_to_file()
        
        # 打印统计信息
        total_sources = sum(len(sources) for sources in self.channel_sources.values())
        print(f"处理完成，共收集 {total_sources} 个直播源")

    def process_url(self, url: str):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                for line in content.splitlines():
                    self.process_channel(line)
        except Exception as e:
            print(f"处理URL失败 {url}: {e}")

if __name__ == "__main__":
    processor = TVChannelProcessor()
    processor.run()
