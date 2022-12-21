from typing import List


def parameterize(cmd: str) -> List[str]:
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


def unparameterize(cmd: List[str]) -> str:
    return " ".join(repr(i) if ' ' in i else i for i in cmd)


DEBUG = True
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
    if DEBUG:
        print(f"{ANSI_CYAN}[DEBUG]{ANSI_RESET}", *args, **kwargs)

def error(*args, **kwargs):
    print(f"{ANSI_RED}[ERROR]{ANSI_RESET}", *args, **kwargs)
