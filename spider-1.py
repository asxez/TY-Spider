from config import wiki, bfs_depth
from log_lg import SpiderLog
from spider import bfs

if __name__ == '__main__':
    SpiderLog()
    bfs(wiki, 'wiki', bfs_depth)
