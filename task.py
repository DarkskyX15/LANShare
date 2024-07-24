'''
Date: 2024-07-17 19:25:23
Author: DarkskyX15
LastEditTime: 2024-07-24 13:52:14
'''

from time import sleep
from os import path, remove
from typing import Literal, Any, BinaryIO
from queue import Queue, Full, Empty
from tool import get_multi_paths, make_short_log, size_to_byte
from logger import LoggerWrapper
from config import LangFile
from threading import Thread
from socket import *
from tcp import *

__all__ = ['MSG_TYPE', 'Msg',
           'get_task_config', 'TaskReleaser', 'MergeFile']

MSG_TYPE = Literal[
    'end', 'single', 'split',
    'block', 'block_end', 'stop_fm',
    'bad_package'
]

class Msg:
    msg: MSG_TYPE
    args: dict[str, Any]
    def __init__(self, msg: MSG_TYPE, args: dict[str, Any]) -> None:
        self.msg = msg
        self.args = args
    def __getitem__(self, key: str) -> Any:
        return self.args.get(key, None)
    def __call__(self, msg: MSG_TYPE) -> bool:
        return self.msg == msg
    
    @staticmethod
    def make_dict(_msg) -> dict[str, Any]:
        return {
            "msg": _msg.msg,
            "args": _msg.args
        }
    @staticmethod
    def make_msg(data: dict[str, Any]):
        if data is None: return Msg('bad_package', {})
        return Msg(data.get('msg', 'bad_package'), data.get('args', {}))

def get_task_config(task_path: str) -> dict[str, Any]:
    task_config: dict[str, Any]
    task_path = task_path.removesuffix('\\')
    if path.isfile(task_path):
        task_config = {
            "task_type": 'file',
            "apex_path": task_path,
            "dir_path": [],
            "file_count": 1,
            "file_path": [task_path],
            "total_size": path.getsize(task_path)
        }
    else:
        task_config = {
            "task_type": 'dir',
            "apex_path": task_path,
        }
        tot_size = 0
        file_path, dir_path = get_multi_paths(task_path)
        for file in file_path:
            tot_size += path.getsize(file)
        task_config['file_path'] = file_path
        task_config['dir_path'] = dir_path
        task_config['total_size'] = tot_size
        task_config['file_count'] = len(file_path)
    return task_config

class TaskReleaser:
    _msg_queue: Queue
    _push_buffer: list[Msg]
    _split_limit: int
    _apex_path: str
    _file_list: list[str]
    _task_type: str
    _thread_cnt: int
    _logger: LoggerWrapper
    _locale: LangFile
    _split_id: int
    def __init__(self, task_info: dict[str, Any],
                 start_info: dict[str, Any],
                 locale: LangFile,
                 logger: LoggerWrapper) -> None:
        self._split_id = 0
        self._msg_queue = Queue(512)
        self._split_limit = size_to_byte(start_info['split_limit'])
        self._thread_cnt = start_info['thread_count']
        self._apex_path = task_info['apex_path']
        self._file_list = task_info['file_path']
        self._task_type = task_info['task_type']
        self._logger = logger
        self._locale = locale
        self._push_buffer = []
    
    def _generate_task(self, file_path: str) -> None:
        file_size = path.getsize(file_path)
        rel_path = file_path.removeprefix(self._apex_path)
        if file_size > 1.5 * (self._split_limit):
            self._logger.info(
                self._locale('send.work.make_task').format('split'),
                make_short_log(file_path)
            )
            block_cnt = file_size // self._split_limit
            final_block = file_size - block_cnt * self._split_limit
            self._msg_queue.put(Msg('split', {
                "size": file_size,
                "sid": self._split_id,
                "path": rel_path,
                "cnt": block_cnt + (1 if final_block > 0 else 0)
            }))
            block_index = 0
            for front in range(0, file_size - final_block, self._split_limit):
                file = open(file_path, 'rb')
                file.seek(front)
                self._msg_queue.put(Msg('block', {
                    "size": self._split_limit,
                    "index": block_index,
                    "file": file,
                    "sid": self._split_id
                }))
                block_index += 1
            if final_block > 0:
                file = open(file_path, 'rb')
                file.seek(block_cnt * self._split_limit)
                self._msg_queue.put(Msg('block', {
                    "size": final_block,
                    "index": block_index,
                    "file": file,
                    "sid": self._split_id
                }))
            self._split_id += 1
        else:
            self._logger.info(
                self._locale('send.work.make_task').format('single'),
                make_short_log(file_path)
            )
            self._msg_queue.put(Msg('single', {
                "file": open(file_path, 'rb'),
                "path": rel_path,
                "size": file_size
            }))

    def _try_push(self) -> None:
        index = 0
        buffer_size = len(self._push_buffer)
        while index < buffer_size:
            try:
                self._msg_queue.put_nowait(self._push_buffer[index])
            except Full:
                sleep(1.0)
                continue
            index += 1
        self._push_buffer.clear()

    def _end_work(self) -> None:
        for _ in range(self._thread_cnt):
            self._push_buffer.append(Msg('end',{
                "reason": self._locale('msg.task_end')
            }))
        self._try_push()

    def loop(self) -> None:
        self._logger.info(self._locale('send.work.loop'))
        if self._task_type == 'dir':
            for file_path in self._file_list:
                self._generate_task(file_path)
                self._try_push()
        elif self._task_type == 'file':
            self._apex_path = '\\'.join(self._apex_path.split('\\')[:-1])
            self._generate_task(self._file_list[0])
            self._try_push()
        self._end_work()
        self._msg_queue.join()
        self._logger.info(self._locale('send.work.end'))
    
    def get_reference(self) -> Queue:
        return self._msg_queue

class MergeFile:
    _msg_queue: Queue
    _logger: LoggerWrapper
    _locale: LangFile
    def __init__(self, locale: str, logger: LoggerWrapper) -> None:
        self._logger = logger
        self._locale = locale
        self._msg_queue = Queue()

    @staticmethod
    def _merge_work(msg_queue: Queue, cnt: int, fpath: str) -> None:
        writer = open(fpath, 'wb')
        merge_buffer: set[int] = set()
        file_io_map: dict[int, tuple[BinaryIO, str]] = {}
        merge_index = 0
        while merge_index < cnt:
            if merge_index in merge_buffer:
                file_io = file_io_map.get(merge_index)
                data = file_io[0].read(4096)
                while data:
                    writer.write(data)
                    data = file_io[0].read(4096)
                file_io[0].close()
                remove(file_io[1])
                merge_buffer.discard(merge_index)
                file_io_map.pop(merge_index)
                merge_index += 1
                continue
            try:
                msg: Msg = msg_queue.get_nowait()
                msg_queue.task_done()
                if msg('block_end'):
                    file_io = open(msg['path'], 'rb')
                    file_io_map[msg['index']] = (file_io, msg['path'])
                    merge_buffer.add(msg['index'])
            except Empty:
                sleep(1.0)
        del merge_buffer, file_io_map
        writer.close()

    @staticmethod
    def _manager_thread(msg_queue: Queue, sock: socket) -> None:
        sock.settimeout(None)
        packer = Packer(Coder(), 'loose')
        while True:
            msg: Msg = Msg.make_msg(packer.recvPacket(sock))
            if msg('stop_fm'):
                msg_queue.put(msg)
                break
        del packer

    def loop(self, manager: socket) -> None:
        self._logger.info(self._locale('recv.file_merge.loop'))
        manager_thread = Thread(
            target=self._manager_thread,
            args=(self._msg_queue, manager)
        )
        manager_thread.start()
        msg_queue_map: dict[int, Queue] = {}
        merge_threads: list[Thread] = []
        while True:
            msg: Msg = self._msg_queue.get()
            self._msg_queue.task_done()
            if msg('stop_fm'):
                self._logger.info(
                    self._locale('recv.file_merge.stop'),
                    msg["reason"]
                )
                break
            elif msg('split'):
                mq = msg_queue_map.get(msg['sid'], None)
                if mq is None:
                    mq = Queue()
                    msg_queue_map[msg['sid']] = mq
                merge_thread = Thread(
                    target=MergeFile._merge_work,
                    args=(mq, msg['cnt'], msg['path'])
                )
                merge_threads.append(merge_thread)
                merge_thread.start()
                self._logger.info(
                    self._locale('recv.file_merge.new_merge').format(
                        msg['sid']
                    ), make_short_log(msg['path'])
                )
            elif msg('block_end'):
                mq = msg_queue_map.get(msg['sid'], None)
                if mq is None:
                    mq = Queue()
                    msg_queue_map[msg['sid']] = mq
                mq.put(msg)
                self._logger.info(
                    self._locale('recv.file_merge.new_block').format(
                        msg['sid'], msg['index']
                    )
                )
        for t in merge_threads: t.join()
        manager_thread.join()
        for index in msg_queue_map.keys():
            msg_queue_map[index].join()
        self._msg_queue.join()

    def get_queue(self) -> Queue:
        return self._msg_queue