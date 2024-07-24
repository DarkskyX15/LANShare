'''
Date: 2024-07-16 19:38:54
Author: DarkskyX15
LastEditTime: 2024-07-24 13:33:45
'''

from logger import ThreadLogger
from tool import *
from broadcast import *
from tcp import *
from config import *
from task import *
from thread import *
from reg_win import *

import os
from socket import *
from sys import argv
from random import randint

if __name__ == '__main__':
    # check install path
    registered = False
    install_path = check_reg()
    if install_path is not None:
        os.chdir(install_path)
        registered = True

    # use lang_file in config
    start_config = JsonFileConfig({
        "save_logs": False,
        "lang_file": r'.\Locales\zh_CN.json',
        "block_cache": r'.\Cache'
    })
    start_config.load_from_file(r'.\Configs\cfg_recv.json')

    # setup logger
    thread_logger = ThreadLogger(start_config['save_logs'], r'.\Logs\Recv')
    thread_logger.startLogThread()
    main_logger = thread_logger.getWrapperInstance('main')

    # setup language
    lang_text = LangFile({})
    lang_text.load_from_file(start_config['lang_file'])

    # show registered
    if not registered:
        main_logger.warn(lang_text('sys.not_registered'))
    else:
        main_logger.info(lang_text('sys.install_path'), install_path)

    # ask for context menu
    if registered: check_menu(main_logger, lang_text)

    # start info
    local_ip = get_local_ip()
    main_port = randint(30000, 60000)
    main_logger.info(lang_text('recv.launch.start').format(local_ip, main_port))

    # get save folder
    if len(argv) >= 2:
        save_folder = argv[1]
        if save_folder.endswith('"'):
            save_folder = save_folder[:-1] + '\\'
        main_logger.info(lang_text('recv.launch.argv'), save_folder)
    else:
        main_logger.info(lang_text('recv.launch.give_save_folder'), end='')
        save_folder = input()
    save_folder.removesuffix('\\')

    # get key
    main_logger.info(lang_text('recv.launch.key_tip'), end='')
    ## validate key
    while True:
        raw_key = input()
        if len(raw_key) != 10:
            main_logger.info(lang_text('recv.launch.fail_key'), end='')
            continue
        try: port = int(raw_key[5:])
        except ValueError:
            main_logger.info(lang_text('recv.launch.fail_key'), end='')
            continue
        else:
            main_logger.info(lang_text('recv.launch.searching'))
            server_ip = BroadcastClient(
                (local_ip, port),
                raw_key
            ).run(main_port)
            break

    # open main
    main_packer = Packer(Coder(), 'loose', main_logger)
    tcp_accept_socket = socket(AF_INET, SOCK_STREAM)
    tcp_accept_socket.bind((local_ip, main_port))
    tcp_accept_socket.settimeout(10.0)
    tcp_accept_socket.listen(5)
    main_logger.info(lang_text('recv.launch.wait_server'))

    # get client & warn timeout
    rp = 0
    while True:
        try:
            info_exchange, connect_addr = tcp_accept_socket.accept()
            # ignore connection not from server
            if server_ip != 'any' and connect_addr[0] != server_ip:
                continue
            info_exchange.settimeout(None)
            break
        except TimeoutError:
            rp += 1
            main_logger.warn(lang_text('recv.launch.wait_timeout').format(rp), end='')
            input()
    del rp

    # recv task with info_exchange
    main_logger.info(lang_text('recv.launch.recv_task'), connect_addr)
    task_config = main_packer.recvPacket(info_exchange)
    ## show task info
    main_logger.info(lang_text('show_task.type'), task_config['type'])
    main_logger.info(lang_text('show_task.file_name'), task_config['file_name'])
    main_logger.info(lang_text('show_task.file_count'), task_config['file_count'])
    main_logger.info(lang_text('show_task.total_size'), task_config['total_size'])
    main_logger.info(lang_text('show_task.thread_cnt'), task_config['thread_cnt'])
    
    # recv dir info
    main_logger.info(lang_text('recv.prepare.folder'))
    dir_path_cnt = main_packer.recvPacket(info_exchange)
    dir_name: str = task_config['file_name']
    dir_paths: list[str] = []
    for index in range(dir_path_cnt):
        rel_path: str = main_packer.recvPacket(info_exchange)
        dir_paths.append(f'{save_folder}\\{dir_name}{rel_path}')
    main_logger.info(lang_text('recv.prepare.folder_cnt'), dir_path_cnt)

    # make apex_path
    if task_config['type'] == 'file':
        apex_path = save_folder
    elif task_config['type'] == 'dir':
        apex_path = f'{save_folder}\\{dir_name}'

    # create dirs
    main_logger.info(lang_text('recv.prepare.create_folder'))
    skip_create: int = 0
    for dir_path in dir_paths:
        try: os.mkdir(dir_path)
        except FileExistsError: skip_create += 1
    if skip_create > 0:
        main_logger.warn(lang_text('recv.prepare.warn_skip'), skip_create)
    del dir_paths, skip_create

    # create MergeFile
    merge_file = MergeFile(lang_text, thread_logger.getWrapperInstance('MergeFile'))
    merge_msg = merge_file.get_queue()

    # create cache folder
    if not os.path.exists(start_config['block_cache']):
        os.makedirs(start_config['block_cache'])
    main_logger.info(lang_text('recv.prepare.cache'), start_config['block_cache'])

    # create RecvThread
    main_logger.info(lang_text('recv.prepare.recv_connect'))
    recv_threads: list[RecvThread] = []
    for i in range(task_config['thread_cnt']):
        connection, addr = tcp_accept_socket.accept()
        recv_threads.append(RecvThread(
            merge_msg, connection, i,
            thread_logger.getWrapperInstance(f'RecvThread{i}'),
            start_config['lang_file'], apex_path, start_config['block_cache']
        ))
    ## launch threads
    for t in recv_threads: t.run()

    # give control to merge_file
    merge_file.loop(info_exchange)
    info_exchange.close()

    # wait join
    main_logger.info(lang_text('recv.work.wait_quit'))
    for t in recv_threads: t.join()

    # save config
    start_config.save_to_file(r'.\Configs\cfg_recv.json')

    main_logger.stopLogger(lang_text('recv.exit'))
    