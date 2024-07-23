'''
Date: 2024-07-16 14:23:04
Author: DarkskyX15
LastEditTime: 2024-07-23 23:09:40
'''

from tool import *
from tcp import *
from broadcast import *
from config import *
from reg_win import *
from logger import ThreadLogger
from task import *
from thread import *

from os import chdir
from socket import *
from random import randint
from sys import argv

if __name__ == '__main__':
    # check install path
    registered = False
    install_path = check_reg()
    if install_path is not None:
        chdir(install_path)
        registered = True

    # start config
    start_config: JsonFileConfig = JsonFileConfig({
        "save_logs": False,
        "thread_count": 20,
        "split_limit": '16MB',
        "lang_file": r'.\Locales\zh_CN.json',
    })
    start_config.load_from_file(r'.\Configs\cfg_send.json')

    # run logger
    thread_logger = ThreadLogger(start_config['save_logs'], r'.\Logs\Send')
    thread_logger.startLogThread()
    main_logger = thread_logger.getWrapperInstance('main')

    # setup language
    lang_text = LangFile({})
    lang_text.load_from_file(start_config['lang_file'])
    main_logger.info(lang_text('send.launch.start'), start_config)

    # show registered
    if not registered:
        main_logger.warn(lang_text('sys.not_registered'))
    else:
        main_logger.info(lang_text('sys.install_path'), install_path)

    # ask context menu
    if registered: check_menu(main_logger, lang_text)

    # get local_ip
    local_ip = get_local_ip()
    main_logger.info(lang_text('send.launch.show_local_ip'), local_ip)

    # get target path
    if len(argv) >= 2:
        target_path = argv[1]
        main_logger.info(lang_text('send.launch.argv'), target_path)
    else:
        main_logger.info(lang_text('send.launch.give_path'), end='')
        target_path = input()

    # get task info
    task_config = get_task_config(target_path)
    ## show task info
    main_logger.info(lang_text('show_task.type'), task_config['task_type'])
    main_logger.info(lang_text('show_task.choose_path'), task_config['apex_path'])
    main_logger.info(lang_text('show_task.file_count'), task_config['file_count'])
    main_logger.info(lang_text('show_task.total_size'), task_config['total_size'])

    # get client address
    key, bc_port = generate_connect_key(5)
    main_logger.warn(lang_text('send.launch.show_key').format(key + str(bc_port)))
    main_logger.info(lang_text('send.launch.searching_client'))
    recv = BroadcastServer(
        ('255.255.255.255', bc_port),
        (local_ip, randint(30000, 60000)),
        key + str(bc_port)
    ).run_till_recv()
    client_addr = (recv['addr_ip'], recv['port'])

    main_logger.info(lang_text('send.launch.client_found'), client_addr)

    # connect to client
    main_packer = Packer(Coder(), 'loose', main_logger)
    info_exchange = socket(AF_INET, SOCK_STREAM)
    info_exchange.connect(client_addr)
    
    # send task info
    main_logger.info(lang_text('send.launch.connected'))
    apex_path: str = task_config['apex_path']
    main_packer.sendPacket(info_exchange, {
        "type": task_config['task_type'],
        "file_name": apex_path.split('\\')[-1],
        "file_count": task_config['file_count'],
        "total_size": task_config['total_size'],
        "thread_cnt": start_config['thread_count']
    })

    # send dir info
    main_logger.info(lang_text('send.prepare.folder'))
    dir_paths: list[str] = task_config['dir_path']
    dir_count = len(dir_paths)
    main_packer.sendPacket(info_exchange, dir_count)
    for dir_path in dir_paths:
        main_packer.sendPacket(info_exchange, dir_path.removeprefix(apex_path))

    # task releaser
    task_releaser = TaskReleaser(
        task_config, start_config,
        lang_text, thread_logger.getWrapperInstance('TaskReleaser')
    )
    task_queue = task_releaser.get_reference()

    # make threads
    send_thread_list: list[SendThread] = []
    for i in range(start_config['thread_count']):
        send_thread_list.append(SendThread(
            task_queue, client_addr, i,
            thread_logger.getWrapperInstance(f'SendThread{i}'),
            start_config['lang_file']
        ))
    ## launch threads
    for t in send_thread_list: t.run()

    # give control to TaskReleaser
    task_releaser.loop()

    # wait join
    main_logger.info(lang_text('send.work.wait_quit'))
    for t in send_thread_list: t.join()

    # send stop fm
    main_packer.sendPacket(info_exchange, Msg.make_dict(
        Msg('stop_fm', {
            "reason": lang_text('msg.task_end')
        })
    ))

    # save config
    start_config.save_to_file(r'.\Configs\cfg_send.json')

    main_logger.stopLogger(lang_text('send.exit'))
