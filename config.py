'''
Date: 2024-07-16 19:43:02
Author: DarkskyX15
LastEditTime: 2024-07-23 21:42:00
'''

__all__ = ['JsonFileConfig', 'LangFile', 'TEXT_KEY']

import json
from typing import Any, Literal

TEXT_KEY = Literal[

    'sys.not_registered',
    'sys.install_path',

    'reg.menu.not_an_admin',
    'reg.menu.not_registered',
    'reg.menu.failed',
    'reg.menu.success',

    'menu.send.file',
    'menu.send.folder',
    'menu.recv',

    'msg.task_end',

    'send.launch.start',
    'send.launch.show_key',
    'send.launch.searching_client',
    'send.launch.show_local_ip',
    'send.launch.client_found',
    'send.launch.give_path',
    'send.launch.connected',
    'send.launch.argv',

    'send.prepare.folder',
    'send.work.loop',
    'send.work.end',
    'send.work.make_task',
    'send.work.wait_quit',

    'send.exit',

    'send.thread.start',
    'send.thread.connect',
    'send.thread.exit',

    'show_task.type',
    'show_task.file_count',
    'show_task.total_size',
    'show_task.choose_path',
    'show_task.thread_cnt',
    'show_task.file_name',

    'recv.launch.start',
    'recv.launch.give_save_folder',
    'recv.launch.key_tip',
    'recv.launch.fail_key',
    'recv.launch.give_port',
    'recv.launch.searching',
    'recv.launch.wait_server',
    'recv.launch.wait_timeout',
    'recv.launch.recv_task',
    'recv.launch.argv',

    'recv.prepare.folder',
    'recv.prepare.folder_cnt',
    'recv.prepare.create_folder',
    'recv.prepare.warn_skip',
    'recv.prepare.recv_connect',
    'recv.prepare.cache',

    'recv.file_merge.loop',
    'recv.file_merge.stop',
    'recv.file_merge.new_merge',
    'recv.file_merge.new_block',

    'recv.work.wait_quit',

    'recv.thread.start',
    'recv.thread.end',
    'recv.thread.bad_package',
    'recv.thread.recv_single',
    'recv.thread.recv_split',
    'recv.thread.recv_block',

    'recv.exit'
]

class JsonFileConfig:
    data_field: dict[str, Any]

    def __init__(self, default: dict[str, Any]) -> None:
        self.data_field = default
    def __getitem__(self, key: str) -> Any:
        return self.data_field[key]
    def __setitem__(self, key: str, value: Any) -> None:
        self.data_field[key] = value
    def __str__(self) -> str:
        return str(self.data_field)

    def load_from_file(self, path: str) -> None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        except FileNotFoundError: return
        except Exception: raise
        cfg_data: dict[str, Any] = json.loads(json_str)
        for key in cfg_data.keys():
            self.data_field[key] = cfg_data[key]
    def save_to_file(self, path: str) -> None:
        json_str = json.dumps(self.data_field, indent = 4)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_str)

class LangFile(JsonFileConfig):
    def __init__(self, default: dict[str, Any]) -> None:
        super().__init__(default)
    def __call__(self, key: TEXT_KEY) -> str:
        return self.data_field.get(key, key)
