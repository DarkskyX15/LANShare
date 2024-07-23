'''
Date: 2024-07-16 20:24:48
Author: DarkskyX15
LastEditTime: 2024-07-23 12:57:49
'''

__all__ = ['bytes_to_size', 'size_to_byte', 'get_multi_paths',
           'SimplePacket', 'generate_connect_key', 'get_local_ip',
           'make_short_log']

from os import walk, path
from typing import Any
from base64 import b64encode, b64decode
from json import dumps, loads
from socket import *
from random import randint

class SimplePacket:
    @staticmethod
    def encode(data: dict[str, Any]) -> bytes:
        try: return b64encode(dumps(data).encode())
        except Exception: return b''
    @staticmethod
    def decode(byte_arr: bytes) -> dict[str, Any] | None:
        try: return loads(b64decode(byte_arr).decode())
        except Exception: return None

def make_short_log(content: str, length: int = 50) -> str:
    if len(content) <= length: return content
    else: return '...' + content[len(content) - length:]

def get_local_ip() -> str:
    st = socket(AF_INET, SOCK_DGRAM)
    try:       
        st.connect(('10.255.255.255', 1))
        local = st.getsockname()[0]
    except Exception:
        local = '127.0.0.1'
    finally:
        st.close()
        return local

def generate_connect_key(size: int) -> str:
    key = ''
    for _ in range(size):
        key += chr(randint(ord('a'), ord('z')))
    return key, randint(30000, 60000)

def bytes_to_size(size_by_bytes: float) -> str:
    if size_by_bytes < 1024:
        size_with_str = str(size_by_bytes) + 'B'
    elif 1024 <= size_by_bytes < 1048576:
        size_by_bytes /= 1024
        size_with_str = str(size_by_bytes) + 'KB'
    elif 1048576 <= size_by_bytes < 1073741824:
        size_by_bytes /= 1048576
        size_with_str = str(size_by_bytes) + 'MB'
    elif 1073741824 <= size_by_bytes:
        size_by_bytes /= 1073741824
        size_with_str = str(size_by_bytes) + 'GB'
    return size_with_str

def size_to_byte(size_by_str: str) -> int:
    if size_by_str.endswith('GB'):
        return int(float(size_by_str[:-2]) * 1073741824) 
    elif size_by_str.endswith('MB'):
        return int(float(size_by_str[:-2]) * 1048576)
    elif size_by_str.endswith('KB'):
        return int(float(size_by_str[:-2]) * 1024)
    else:
        return int(float(size_by_str[:-1]))

def get_multi_paths(folder_path: str) -> tuple[list[str], list[str]]:
    r"""
    返回一对路径列表:`(file_paths, folder_paths)`
    - `file_paths`:`folder_path`下所有文件的路径列表
    - `folder_paths`:`folder_path`下所有文件夹的路径列表 (包括`folder_path`本身)
    """
    file_path_list: list[str] = list()
    folder_list: list[str] = list()
    for filepath, _, filenames in walk(folder_path):
        for filename in filenames:
            file_path_list.append(path.join(filepath, filename))
        folder_list.append(filepath)
    return (file_path_list, folder_list)

