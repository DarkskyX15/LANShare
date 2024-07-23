'''
Date: 2024-07-21 18:26:41
Author: DarkskyX15
LastEditTime: 2024-07-23 23:08:10
'''

from config import LangFile
from queue import Queue
from threading import Thread
from logger import LoggerWrapper
from task import Msg
from tcp import *
from tool import make_short_log
from socket import *
from typing import BinaryIO

__all__ = ['SendThread', 'RecvThread']

class SendThread:
    _locale: LangFile
    _work_thread: Thread
    _msg_queue: Queue
    _logger: LoggerWrapper
    _uid: int
    _connection: socket
    def __init__(self, msg_queue: Queue, client_addr: tuple[str, int], uid: int,
                 logger: LoggerWrapper, lang: str) -> None:
        self._locale = LangFile({})
        self._locale.load_from_file(lang)
        self._msg_queue = msg_queue
        self._work_thread = Thread(target=self._work)
        self._uid = uid
        self._logger = logger
        self._logger.info(self._locale('send.thread.connect'))
        self._connection = socket(AF_INET, SOCK_STREAM)
        self._connection.connect(client_addr)
    
    def _read_and_send(self, file: BinaryIO, size: int, packer: Packer) -> None:
        while size > 0:
            read_size = min(4096, size)
            packer.sendPacket(
                self._connection, file.read(read_size),
                serialization_method=SM_RAW
            )
            size -= read_size
        file.close()

    def _work(self) -> None:
        packer = Packer(Coder(), 'loose', self._logger)
        while True:
            msg: Msg = self._msg_queue.get()
            self._msg_queue.task_done()
            if msg('end'):
                packer.sendPacket(self._connection, Msg.make_dict(msg))
                packer.recvPacket(self._connection, None, SM_RAW)
                self._logger.info(
                    self._locale('send.thread.exit').format(self._uid),
                    msg['reason']
                )
                break
            elif msg('split'):
                packer.sendPacket(self._connection, Msg.make_dict(msg))
            elif msg('single'):
                packer.sendPacket(self._connection, Msg.make_dict(
                    Msg('single', {
                        "path": msg['path'],
                        "size": msg['size']
                    })
                ))
                self._read_and_send(msg['file'], msg['size'], packer)
            elif msg('block'):
                packer.sendPacket(self._connection, Msg.make_dict(
                    Msg('block', {
                        "size": msg['size'],
                        "index": msg['index'],
                        "sid": msg['sid']
                    })
                ))
                self._read_and_send(msg['file'], msg['size'], packer)
            packer.recvPacket(self._connection, None, SM_RAW)
        self._connection.close()

    def join(self) -> None:
        self._work_thread.join()

    def run(self) -> None:
        self._logger.info(self._locale('send.thread.start').format(self._uid))
        self._work_thread.start()

class RecvThread:
    _connection: socket
    _locale: LangFile
    _msg_queue: Queue
    _logger: LoggerWrapper
    _thread: Thread
    _uid: int
    _apex_path: str
    _cache: str
    def __init__(self, msg_queue: Queue, connection: socket, uid: int,
                 logger: LoggerWrapper, lang: str, apex_path: str, cache: str) -> None:
        self._locale = LangFile({})
        self._locale.load_from_file(lang)
        self._connection = connection
        self._connection.settimeout(10.0)
        self._msg_queue = msg_queue
        self._logger = logger
        self._apex_path = apex_path
        self._uid = uid
        self._cache = cache.removesuffix('\\')
        self._thread = Thread(target=self._work)

    def _recv_file(self, packer: Packer, file: BinaryIO, size: int) -> None:
        recv_size: int = 0
        while recv_size < size:
            data: bytes = packer.recvPacket(
                self._connection, None,
                serialization_method=SM_RAW
            )
            file.write(data)
            recv_size += len(data)
        file.close()

    def _work(self) -> None:
        packer = Packer(Coder(), 'loose', self._logger)
        while True:
            msg: Msg = Msg.make_msg(packer.recvPacket(self._connection))
            if msg('bad_package'):
                self._logger.warn(self._locale('recv.thread.bad_package'))
            elif msg('end'):
                packer.sendPacket(self._connection, b'beat', None, SM_RAW)
                self._logger.info(
                    self._locale('recv.thread.end').format(self._uid),
                    msg['reason']
                )
                break
            elif msg('split'):
                self._logger.info(
                    self._locale('recv.thread.recv_split'),
                    make_short_log(self._apex_path + msg['path'])
                )
                self._msg_queue.put(Msg('split', {
                    "sid": msg['sid'],
                    "path": self._apex_path + msg['path'],
                    "cnt": msg['cnt']
                }))
            elif msg('block'):
                sid = msg['sid']
                idx = msg['index']
                file_path = f'{self._cache}\\{sid}_{idx}.block'
                file = open(file_path, 'wb')
                self._recv_file(packer, file, msg['size'])
                self._logger.info(
                    self._locale('recv.thread.recv_block').format(
                        sid, idx
                    )
                )
                self._msg_queue.put(Msg('block_end', {
                    "sid": sid,
                    "index": idx,
                    "path": file_path
                }))
            elif msg('single'):
                file_path = self._apex_path + msg['path']
                file = open(file_path, 'wb')
                self._recv_file(packer, file, msg['size'])
                self._logger.info(
                    self._locale('recv.thread.recv_single'),
                    make_short_log(file_path)
                )
            packer.sendPacket(self._connection, b'beat', None, SM_RAW)
        self._connection.close()

    def join(self) -> None:
        self._thread.join()

    def run(self) -> None:
        self._logger.info(self._locale('recv.thread.start'), self._uid)
        self._thread.start()
