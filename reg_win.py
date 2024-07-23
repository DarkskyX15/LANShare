'''
Date: 2024-07-18 18:21:22
Author: DarkskyX15
LastEditTime: 2024-07-23 22:13:29
'''

from os import getcwd
from logger import LoggerWrapper
from config import LangFile
from winreg import *
import ctypes, traceback

__all__ = ['check_reg', 'uninstall_menu', 'check_menu']

BASE_KEY = r"SOFTWARE\Darksky\LANShare"
DIRECTORY_KEY = r"Directory\shell\LANShare"
DIRECTORY_CMD_KEY = r"Directory\shell\LANShare\command"
FILE_KEY = r"*\shell\LANShare"
FILE_CMD_KEY = r"*\shell\LANShare\command"
BG_KEY = r"Directory\Background\shell\LANShare"
BG_CMD_KEY = r"Directory\Background\shell\LANShare\command"

def check_admin() -> bool:
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def register_menu(logger: LoggerWrapper, locale: LangFile) -> None:
    if not check_admin():
        logger.error(locale('reg.menu.not_an_admin'))
        return
    try:
        with OpenKey(HKEY_LOCAL_MACHINE, BASE_KEY) as reg:
            cwd_path: str = QueryValueEx(reg, 'Path')[0]
        send_path = cwd_path + '\\Thrower.exe'
        catch_path = cwd_path + '\\Catcher.exe'
        # base key / MenuRegistered'
        with OpenKey(HKEY_LOCAL_MACHINE, BASE_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, 'MenuRegistered', 0, REG_SZ, 'true')
        # send dir
        CreateKey(HKEY_CLASSES_ROOT, DIRECTORY_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, DIRECTORY_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, locale('menu.send.folder'))
            SetValueEx(reg, 'Icon', 0, REG_SZ, send_path)
        CreateKey(HKEY_CLASSES_ROOT, DIRECTORY_CMD_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, DIRECTORY_CMD_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, f'"{send_path}" "%1"')
        # send file
        CreateKey(HKEY_CLASSES_ROOT, FILE_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, FILE_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, locale('menu.send.file'))
            SetValueEx(reg, 'Icon', 0, REG_SZ, send_path)
        CreateKey(HKEY_CLASSES_ROOT, FILE_CMD_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, FILE_CMD_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, f'"{send_path}" "%1"')
        # recv
        CreateKey(HKEY_CLASSES_ROOT, BG_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, BG_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, locale('menu.recv'))
            SetValueEx(reg, 'Icon', 0, REG_SZ, catch_path)
        CreateKey(HKEY_CLASSES_ROOT, BG_CMD_KEY)
        with OpenKey(HKEY_CLASSES_ROOT, BG_CMD_KEY, 0, KEY_WRITE) as reg:
            SetValueEx(reg, '', 0, REG_SZ, f'"{catch_path}" "%V"')
        logger.info(locale('reg.menu.success'))
    except OSError as e:
        logger.error(locale('reg.menu.failed'), e)

def uninstall_menu() -> None:
    if not check_admin():
        print('[错误]无管理员权限，请尝试以管理员身份运行。')
        print("[Error]No administrator rights, try running as administrator.")
        return
    try:
        DeleteKey(HKEY_LOCAL_MACHINE, BASE_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, DIRECTORY_CMD_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, DIRECTORY_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, BG_CMD_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, BG_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, FILE_CMD_KEY)
        DeleteKey(HKEY_CLASSES_ROOT, FILE_KEY)
    except OSError:
        traceback.print_exc()
        return
    print('卸载完成。')
    print('Uninstalled.')

def register_path() -> None:
    cwd = getcwd()
    CreateKey(HKEY_LOCAL_MACHINE, BASE_KEY)
    with OpenKey(HKEY_LOCAL_MACHINE, BASE_KEY, 0, KEY_WRITE) as reg:
        SetValueEx(reg, 'Path', 0, REG_SZ, cwd)
    return cwd

def check_menu(logger: LoggerWrapper, locale: LangFile) -> None:
    try:
        with OpenKey(HKEY_LOCAL_MACHINE, BASE_KEY) as reg:
            QueryValueEx(reg, 'MenuRegistered')
    except OSError:
        logger.info(locale('reg.menu.not_registered'), end='')
        choice = input()
        if choice == 'Y':
            register_menu(logger, locale)

def check_reg() -> str | None:
    try:
        with OpenKey(HKEY_LOCAL_MACHINE, BASE_KEY) as reg:
            return QueryValueEx(reg, 'Path')[0]
    except OSError:
        if not check_admin():
            print('首次运行请以管理员身份启动。')
            print("Please run the application with 'Run as administrator' for its first launch.")
            return None
        else:
            try: return register_path()
            except OSError:
                traceback.print_exc()
                return None
