import re
import os
import sys
import inspect

import ctypes
import termios

from typing import Tuple


class FunctionInfo:
    """The info of a function (filename and lineno)"""
    lineno = -1
    filename = "unknown"
    function = "unknown function"

    def __repr__(self):
        return f"{self.filename}:{self.lineno}"

    def __len__(self):
        return len(self.__repr__())
    

def move_caret_newline() -> None:
    """Prints a newline if the caret is not already on a blank line"""
    if get_caret_position()[0] != 1:
        print()
    return


def get_caller_info() -> FunctionInfo:
    """Gets the information of the caller of the function via python inspect"""
    stacktrace = inspect.stack()
    frame_info = inspect.getframeinfo(stacktrace[2][0])

    ret = FunctionInfo()
    ret.filename = os.path.basename(frame_info.filename)
    ret.function = frame_info.function
    ret.lineno = frame_info.lineno
    return ret


def supports_unicode() -> bool:
    """Returns True if the terminal supports unicode, false otherwise"""
    if sys.stdout.encoding != None:
        return sys.stdout.encoding.lower().startswith('utf')
    return False


def supports_color() -> bool:
    """Return True if the running system's terminal supports color (ANSI),
    and False otherwise. Taken from https://github.com/django/django/blob/
    47c608202a58c8120d049c98d5d27c4609551d33/django/core/management/color.py#L28
    """

    def vt_codes_enabled_in_windows_registry():
        """Check the Windows Registry to see if VT code handling has been enabled
        by default, see https://superuser.com/a/1300251/447564.
        """
        try:
            import winreg
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Console") # type: ignore
            reg_key_value, _ = winreg.QueryValueEx(reg_key, "VirtualTerminalLevel") # type: ignore
        except ImportError:
            return False
        except FileNotFoundError:
            return False
        return reg_key_value == 1

    is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    return is_a_tty and (
        sys.platform != "win32"
        or "ANSICON" in os.environ
        or "WT_SESSION" in os.environ
        or os.environ.get("TERM_PROGRAM") == "vscode"
        or vt_codes_enabled_in_windows_registry()
    )


def get_caret_position() -> Tuple[int, int]:
    """Gets the caret position in terms of x and y (row and col). 
    Taken from https://stackoverflow.com/questions/35526014/
    how-can-i-get-the-cursors-position-in-an-ansi-terminal?noredirect=1&lq=1
    """
    if not supports_color():  # Default to printing a newline if the terminal
        print()               # does not support ANSI escape codes
        return (-1, -1)
    if sys.platform == "win32":
        OldStdinMode = ctypes.wintypes.DWORD() # type: ignore
        OldStdoutMode = ctypes.wintypes.DWORD() # type: ignore
        kernel32 = ctypes.windll.kernel32
        kernel32.GetConsoleMode(kernel32.GetStdHandle(-10), ctypes.byref(OldStdinMode))
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 0)
        kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(OldStdoutMode))
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    else:
        OldStdinMode = termios.tcgetattr(sys.stdin)
        _ = termios.tcgetattr(sys.stdin)
        _[3] = _[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, _)
    try:
        _ = ""
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()
        while not (_ := _ + sys.stdin.read(1)).endswith('R'):
            pass
        res = re.match(r".*\[(?P<y>\d*);(?P<x>\d*)R", _)
    finally:
        if sys.platform == "win32":
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), OldStdinMode)
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), OldStdoutMode)
        else:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, OldStdinMode)
    if res:
        return (int(res.group("x")), int(res.group("y")))
    return (-1, -1)
