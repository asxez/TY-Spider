from config import bfs_depth
from log_lg import SpiderLog
from spider import bfs

if __name__ == '__main__':
    SpiderLog()
    bfs('https://www.asxe.vip', 'asxe', bfs_depth)
