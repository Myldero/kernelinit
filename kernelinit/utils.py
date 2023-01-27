from typing import List, Optional
import glob
import os


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')


def get_file(expr: str) -> Optional[str]:
    """
    Recursively look for filename
    """
    l = glob.glob(f"**/{expr}", recursive=True)
    if l:
        return l[0]
    return None


def parameterize(cmd: str) -> List[str]:
    """
    Create argument list from bash command
    """
    out = []
    curr = ""
    quote = None
    backslash = False
    for c in cmd:
        if backslash:
            if c != '\n':
                curr += c
            backslash = False
        elif c == '\\' and quote != "'":
            backslash = True
        elif quote is None and c in ("'", '"'):
            quote = c
        elif c == quote:
            quote = None
        elif quote is None and c in (' ', '\t'):
            if curr:
                out.append(curr)
                curr = ""
        elif c == '\n':
            break
        else:
            curr += c
    if quote:
        raise Exception("Unfinished quote")

    if curr:
        out.append(curr)
    return out


def unparameterize(cmd: List[str], pretty: bool = False) -> str:
    """
    Create bash command from argument list
    """
    out = ""
    for arg in cmd:
        if pretty and arg.startswith("-"):
            out += " \\\n    "
        elif out:
            out += " "
        if any(i in arg for i in (' ', '"', "'")):
            out += repr(arg)
        else:
            out += arg
    return out


ANSI_RESET  = "\u001b[0m"
ANSI_YELLOW = "\u001b[33m"
ANSI_BLUE   = "\u001b[34m"
ANSI_CYAN   = "\u001b[36m"
ANSI_RED    = "\u001b[31m"

def important(*args, **kwargs):
    print(f"{ANSI_YELLOW}[IMPORTANT]{ANSI_RESET}", *args, **kwargs)

def info(*args, **kwargs):
    print(f"{ANSI_BLUE}[INFO]{ANSI_RESET}", *args, **kwargs)

def debug(*args, **kwargs):
    if hasattr(debug, 'verbose') and debug.verbose:
        print(f"{ANSI_CYAN}[DEBUG]{ANSI_RESET}", *args, **kwargs)

def error(*args, **kwargs):
    print(f"{ANSI_RED}[ERROR]{ANSI_RESET}", *args, **kwargs)

def fatal(*args, **kwargs):
    error(*args, **kwargs)
    exit(-1)
