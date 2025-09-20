import urllib.request
from urllib.parse import urlparse
import re
import os
from datetime import datetime, timedelta, timezone
import random
import opencc
from typing import List, Set, Dict, Tuple

class TVChannelProcessor:
    def __init__(self):
        self.timestart = datetime.now()
        self.combined_blacklist = set()
        self.all_urls = set()  # For global URL deduplication
        
        # Initialize all channel containers
        self.init_channel_containers()
        
    def init_channel_containers(self):
        # Main channels
        self.ys_lines = []  # CCTV channels
        self.ws_lines = []  # Satellite TV channels
        self.ty_lines = []  # Sports channels
        self.dy_lines = []  # Movie channels
        self.dsj_lines = []  # TV drama channels
        self.gat_lines = []  # Hong Kong/Macau/Taiwan channels
        self.twt_lines = []  # Taiwan channels
        self.gj_lines = []  # International channels
        self.jlp_lines = []  # Documentary channels
        self.xq_lines = []  # Opera channels
        self.js_lines = []  # Commentary channels
        self.newtv_lines = []  # NewTV
        self.ihot_lines = []  # iHot
        self.et_lines = []  # Children channels
        self.zy_lines = []  # Variety channels
        self.mdd_lines = []  #埋堆堆
        self.yy_lines = []  # Music channels
        self.game_lines = []  # Game channels
        self.radio_lines = []  # Radio channels
        self.zb_lines = []  # Live China
        self.cw_lines = []  # Spring Festival Gala
        self.mtv_lines = []  # MTV
        self.migu_lines = []  # Migu Live

        # Local channels
        self.sh_lines = []  # Shanghai
        self.zj_lines = []  # Zhejiang
        # ... (other local channels initialized similarly)
        
        self.other_lines = []  # Other channels
        self.removal_list = ["「IPV4」","「IPV6」","[ipv6]","[ipv4]","_电信", "电信","（HD）","[超清]","高清","超清", "-HD","(HK)","AKtv","@","IPV6","🎞️","🎦"," ","[BD]","[VGA]","[HD]","[SD]","(1080p)","(720p)","(480p)"]

    def read_txt_to_array(self, file_name: str) -> List[str]:
        """Read text file into array of lines"""
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            print(f"File '{file_name}' not found.")
            return []
        except Exception as e:
            print(f"An error occurred reading {file_name}: {e}")
            return []

    def read_blacklist_from_txt(self, file_path: str) -> List[str]:
        """Read blacklist from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            return [line.split(',')[1].strip() for line in lines if ',' in line]
        except Exception as e:
            print(f"Error reading blacklist {file_path}: {e}")
            return []

    def load_corrections_name(self, filename: str) -> Dict[str, str]:
        """Load channel name corrections"""
        corrections = {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(',')
                        correct_name = parts[0]
                        for name in parts[1:]:
                            corrections[name] = correct_name
        except Exception as e:
            print(f"Error loading corrections: {e}")
        return corrections

    def traditional_to_simplified(self, text: str) -> str:
        """Convert traditional Chinese to simplified Chinese"""
        try:
            converter = opencc.OpenCC('t2s')
            return converter.convert(text)
        except Exception as e:
            print(f"Error in traditional to simplified conversion: {e}")
            return text

    def is_m3u_content(self, text: str) -> bool:
        """Check if content is M3U format"""
        lines = text.splitlines()
        return lines and lines[0].strip().startswith("#EXTM3U")

    def convert_m3u_to_txt(self, m3u_content: str) -> str:
        """Convert M3U content to TXT format"""
        lines = m3u_content.split('\n')
        txt_lines = []
        channel_name = ""
        
        for line in lines:
            if line.startswith("#EXTM3U"):
                continue
            if line.startswith("#EXTINF"):
                channel_name = line.split(',')[-1].strip()
            elif line.startswith(("http", "rtmp", "p3p")):
                txt_lines.append(f"{channel_name},{line.strip()}")
            
            # Handle M3U files with TXT content
            if "#genre#" not in line and "," in line and "://" in line:
                pattern = r'^[^,]+,[^\s]+://[^\s]+$'
                if re.match(pattern, line):
                    txt_lines.append(line)
        
        return '\n'.join(txt_lines)

    def clean_url(self, url: str) -> str:
        """Remove content after $ in URL"""
        last_dollar_index = url.rfind('$')
        return url[:last_dollar_index] if last_dollar_index != -1 else url

    def clean_channel_name(self, channel_name: str) -> str:
        """Clean channel name by removing unwanted patterns"""
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
            
        return channel_name

    def process_channel_line(self, line: str):
        """Process a single channel line and categorize it"""
        if "#genre#" not in line and "#EXTINF:" not in line and "," in line and "://" in line:
            try:
                channel_name, channel_address = line.split(',', 1)
                channel_name = self.traditional_to_simplified(channel_name)
                channel_name = self.clean_channel_name(channel_name)
                channel_name = self.corrections_name.get(channel_name, channel_name).strip()
                
                channel_address = self.clean_url(channel_address).strip()
                line = f"{channel_name},{channel_address}"
                
                if not channel_address or channel_address in self.combined_blacklist:
                    return
                    
                if channel_address in self.all_urls:
                    return
                    
                self.all_urls.add(channel_address)
                
                # Categorize channels
                self.categorize_channel(channel_name, line)
                
            except Exception as e:
                print(f"Error processing channel line: {e}")

    def categorize_channel(self, channel_name: str, line: str):
        """Categorize channel based on its name"""
        # This would be a large method mapping channel names to categories
        # For brevity, I'm showing just a few examples
        if channel_name in self.ys_dictionary:
            self.ys_lines.append(line)
        elif channel_name in self.ws_dictionary:
            self.ws_lines.append(line)
        elif channel_name in self.newtv_dictionary:
            self.newtv_lines.append(line)
        else:
            self.other_lines.append(line)

    def process_url(self, url: str):
        """Process a URL to extract channel information"""
        print(f"Processing URL: {url}")
        self.other_lines.append(f"{url},#genre#")
        
        try:
            headers = {'User-Agent': 'PostmanRuntime-ApipostRuntime/1.1.0'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                
                # Try different encodings
                encodings = ['utf-8', 'gbk', 'iso-8859-1']
                text = None
                
                for encoding in encodings:
                    try:
                        text = data.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if text is None:
                    print(f"Could not decode content from {url}")
                    return
                
                # Convert M3U to TXT if needed
                if self.is_m3u_content(text):
                    text = self.convert_m3u_to_txt(text)
                
                # Process each line
                lines = text.split('\n')
                print(f"Lines: {len(lines)}")
                
                for line in lines:
                    if "#genre#" not in line and "," in line and "://" in line:
                        channel_name, channel_address = line.split(',', 1)
                        
                        if "#" not in channel_address:
                            self.process_channel_line(line)
                        else:
                            url_list = channel_address.split('#')
                            for channel_url in url_list:
                                newline = f'{channel_name},{channel_url}'
                                self.process_channel_line(newline)
                
                self.other_lines.append('\n')
                
        except Exception as e:
            print(f"Error processing URL {url}: {e}")

    def sort_data(self, order: List[str], data: List[str]) -> List[str]:
        """Sort data based on a specified order"""
        order_dict = {name: i for i, name in enumerate(order)}
        
        def sort_key(line):
            name = line.split(',')[0]
            return order_dict.get(name, len(order))
        
        return sorted(data, key=sort_key)

    def make_m3u(self, txt_file: str, m3u_file: str):
        """Convert TXT file to M3U format"""
        try:
            output_text = '#EXTM3U x-tvg-url="https://epg.112114.xyz/pp.xml.gz"\n'
            
            with open(txt_file, "r", encoding='utf-8') as file:
                input_text = file.read()

            lines = input_text.strip().split("\n")
            group_name = ""
            
            for line in lines:
                parts = line.split(",")
                if len(parts) == 2 and "#genre#" in line:
                    group_name = parts[0]
                elif len(parts) == 2:
                    channel_name = parts[0]
                    channel_url = parts[1]
                    logo_url = f"https://epg.112114.xyz/logo/{channel_name}.png"
                    
                    output_text += f'#EXTINF:-1 tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{group_name}",{channel_name}\n'
                    output_text += f"{channel_url}\n"

            with open(m3u_file, "w", encoding='utf-8') as file:
                file.write(output_text)
                
            print(f"M3U file '{m3u_file}' generated successfully.")
            
        except Exception as e:
            print(f"Error generating M3U file: {e}")

    def run(self):
        """Main execution method"""
        # Load blacklists
        blacklist_auto = self.read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_auto.txt')
        blacklist_manual = self.read_blacklist_from_txt('assets/whitelist-blacklist/blacklist_manual.txt')
        self.combined_blacklist = set(blacklist_auto + blacklist_manual)
        
        # Load whitelists
        self.whitelist_lines = self.read_txt_to_array('assets/whitelist-blacklist/whitelist_manual.txt')
        self.whitelist_auto_lines = self.read_txt_to_array('assets/whitelist-blacklist/whitelist_auto.txt')
        
        # Load channel dictionaries
        self.ys_dictionary = self.read_txt_to_array('主频道/央视频道.txt')
        self.ws_dictionary = self.read_txt_to_array('主频道/卫视频道.txt')
        # ... load other dictionaries
        
        # Load name corrections
        self.corrections_name = self.load_corrections_name('assets/corrections_name.txt')
        
        # Load custom URLs
        urls = self.read_txt_to_array('assets/urls.txt')
        
        # Process whitelists
        self.other_lines.append("白名单,#genre#")
        for line in self.whitelist_lines:
            self.process_channel_line(line)
            
        self.other_lines.append("白名单测速,#genre#")
        for line in self.whitelist_auto_lines:
            if "#genre#" not in line and "," in line and "://" in line:
                parts = line.split(",")
                try:
                    response_time = float(parts[0].replace("ms", ""))
                    if response_time < 2000:  # 2 seconds
                        self.process_channel_line(",".join(parts[1:]))
                except ValueError:
                    print(f"Invalid response time: {line}")
        
        # Process URLs
        for url in urls:
            if url.startswith("http"):
                self.process_url(url)
        
        # Generate output files
        self.generate_output_files()
        
        # Generate M3U files
        self.make_m3u("live.txt", "live.m3u")
        self.make_m3u("live_lite.txt", "live_lite.m3u")
        
        # Print statistics
        self.print_statistics()

    def generate_output_files(self):
        """Generate the output TXT files"""
        # Get current time
        utc_time = datetime.now(timezone.utc)
        beijing_time = utc_time + timedelta(hours=8)
        formatted_time = beijing_time.strftime("%Y%m%d %H:%M")
        
        about_video1 = "https://d.kstore.dev/download/8880/%E5%85%AC%E5%91%8A.mp4"
        about_video2 = "https://v.cdnlz12.com/20250131/18183_a5e8965b/index.m3u8"
        version = f"{formatted_time},{about_video1}"
        about = f"关于本源(塔利班维护),{about_video2}"
        
        # Generate content for simple version
        all_lines_simple = [
            "更新时间,#genre#", version, about, '\n',
            "央视频道,#genre#"
        ] + self.read_txt_to_array('专区/央视频道.txt') + self.sort_data(self.ys_dictionary, self.ys_lines) + ['\n'] + [
            "卫视频道,#genre#"
        ] + self.read_txt_to_array('专区/卫视频道.txt') + self.sort_data(self.ws_dictionary, self.ws_lines) + ['\n']
        # ... continue building the content
        
        # Generate content for full version
        all_lines = all_lines_simple + [
            # ... add more categories
        ]
        
        # Write files
        try:
            with open("live_lite.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_lines_simple))
            print("精简版文本已保存到文件: live_lite.txt")
            
            with open("live.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_lines))
            print("完整版文本已保存到文件: live.txt")
            
            with open("others.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.other_lines))
            print("其他频道已保存到文件: others.txt")
            
        except Exception as e:
            print(f"保存文件时发生错误：{e}")

    def print_statistics(self):
        """Print execution statistics"""
        timeend = datetime.now()
        elapsed_time = timeend - self.timestart
        total_seconds = elapsed_time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        
        print(f"执行时间: {minutes} 分 {seconds} 秒")
        print(f"blacklist行数: {len(self.combined_blacklist)}")
        print(f"live.txt行数: {len(self.all_urls)}")
        print(f"others.txt行数: {len(self.other_lines)}")

if __name__ == "__main__":
    processor = TVChannelProcessor()
    processor.run()

