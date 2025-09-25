已有zb网址在urls.txt文件内生成zb源。此代码注释详细！直播源自动化检测与分类工具。
1、.github/workflows/whitelist-blacklist.yml名WhiteList BlackList，执行assets/whitelist-blacklist/main.py。从assets/urls.txt（远程直播源）、live.txt、others.txt（本地直播源）、whitelist_manual.txt（手动维护的白名单）读取直播源，验证有效性后生成./assets/whitelist-blacklist/下：黑名单blacklist_auto.txt（拦截直播源）、blackhost_count.txt（统计无效域名出现次数）；白名单whitelist_auto.txt（仅保留响应时间<2秒高质量源）；whitelist_auto_tv.txt（有效URL，供播放器直接使用）及既不在黑名单也不在白名单other_lines)。手动维护黑名单blacklist_manual、白名单whitelist_manual.txt。
2、.github/workflows/main.yml，名Daily Job，运行main.py。从assets/urls.txt及本地文件白名单中获取直播源，自动过滤黑名单，保留白名单。生成完整zb源live.txt（含所有分类）、live.m3u及精简live_lite.txtlive_lite.m3u（仅央视、卫视等）， others.txt（未分类频道）。
3、assets/corrections_name.txt下为需要的中央台。主频道内为需要中央台、NewTV及卫视台。地方台下为需要的各省地方台。三者均可修改但不能没有。原来的专区也不可无。



