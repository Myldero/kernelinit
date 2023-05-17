import os
import pexpect
import re

from .runfile import RunFile
from .utils import unparameterize, debug, info, important, error


def do_unintended_checks(runfile: RunFile):
    """
    Check for unintended solutions by enumerating file permissions
    """
    cmd = unparameterize(runfile.create_release_run())

    info("Running unintended checks...")
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    def send_cmd(c):
        child.sendline(c); child.readline()
        child.expect_exact(b'$ ')
        return ansi_escape.sub('', child.before.decode(errors='ignore'))

    visited = set()
    def get_writable(dirname, message):
        if dirname in visited:
            return
        visited.add(dirname)
        debug(f"get_writable('{dirname}')")
        if dirname != '/':
            get_writable(os.path.dirname(dirname), message)

        out = send_cmd(f"ls -ld '{dirname}'").strip()
        if 'cannot access' in out:
            return
        elif f'{dirname} -> ' in out:
            new_name = re.findall(f'{dirname} -> (.*\S)', out)[0]
            get_writable(os.path.normpath(os.path.join(os.path.dirname(dirname), new_name)), message)
            return
        perms, _, fuid, *_ = out.split()
        if perms[-3:-1] == 'rw' or fuid in (uid, uidname):
            important(f"Write-access to '{dirname}'.", message)

    child = pexpect.spawn(cmd)
    try:
        child.expect_exact(b'$ ', timeout=60)
    except Exception as e:
        if isinstance(e, pexpect.exceptions.TIMEOUT):
            reason = "time out"
        elif isinstance(e, pexpect.exceptions.EOF):
            reason = "EOF"
        else:
            reason = "unknown error"
        error(f"Unintended checks failed due to {reason}")
        debug(e)
        child.sendeof()
        child.kill(9)
        return
    my_id = send_cmd('id').strip().split()
    uid, *uidname = my_id[0][4:].split("(")
    uidname = uidname[0][:-1] if uidname else None
    debug("uid:", uid, uidname)
    get_writable('/sbin/modprobe', message='Unintended by hijacking /sbin/modprobe')
    get_writable('/etc/passwd', message='Unintended by overwriting /etc/passwd (If busybox is SUID)')
    child.sendeof()
    child.kill(9)
    info("Finished unintended checks")
