import gdb

class ShowTaskCreds(gdb.Command):
    """Escalate privileges on specific pid: make-root <pid>"""

    def __init__(self):
        super().__init__("make-root", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        argv = gdb.string_to_argv(arg)
        if len(argv) != 1:
            print("Usage: make-root <pid>")
            return

        target_pid = int(argv[0])
        task_struct_ptr_t = gdb.lookup_type("struct task_struct").pointer()

        init_task_addr = gdb.parse_and_eval("&init_task")
        init_task = init_task_addr.cast(task_struct_ptr_t)
        task = init_task

        while True:
            pid = int(task.dereference()["pid"])
            if pid == target_pid:
                cred = task.dereference()["cred"]

                for field in ["uid", "gid", "euid", "egid", "suid", "sgid", "fsuid", "fsgid"]:
                    addr = cred.dereference()[field]["val"].address
                    gdb.execute(f'set *(int*){addr} = 0')
                
                for field in ["cap_permitted", "cap_effective", "cap_bset"]:
                    addr = cred.dereference()[field]["val"].address
                    gdb.execute(f'set *(long*){addr} = 0x1ffffffffff')
                
                print("Success!")
                return

            next_task = task.dereference()["tasks"]["next"]
            offset = int(gdb.parse_and_eval(
                "(unsigned long)&((struct task_struct *)0)->tasks"
            ))
            task = (next_task.cast(gdb.lookup_type("char").pointer()) - offset).cast(
                gdb.lookup_type("struct task_struct").pointer()
            )

            if task == init_task:
                print(f"PID {target_pid} not found")
                return

def per_cpu_ptr(symbol, cpu, typ):
    base = int(gdb.parse_and_eval(f"(unsigned long)&{symbol}"))
    off = int(gdb.parse_and_eval(f"__per_cpu_offset[{cpu}]"))
    return gdb.Value((base + off) % 2**64).cast(typ.pointer())

def current_tasks_by_cpu():
    rq_t = gdb.lookup_type("struct rq")
    task_ptr_t = gdb.lookup_type("struct task_struct").pointer()

    nr_cpu_ids = int(gdb.parse_and_eval("nr_cpu_ids"))
    curr = {}

    for cpu in range(nr_cpu_ids):
        try:
            rq = per_cpu_ptr("runqueues", cpu, rq_t)
            task = rq.dereference()["curr"].cast(task_ptr_t)
            curr[int(task)] = cpu
        except gdb.error:
            pass

    return curr

class KernelPs(gdb.Command):
    """Simple kernel ps: shows PID, PPID, CMD"""

    def __init__(self):
        super().__init__("kps", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        task_struct_ptr_t = gdb.lookup_type("struct task_struct").pointer()

        # Get init_task safely even if typing is missing
        try:
            init_task = gdb.parse_and_eval("&init_task").cast(task_struct_ptr_t)
        except gdb.error:
            addr = int(gdb.parse_and_eval("(unsigned long)&init_task"))
            init_task = gdb.Value(addr).cast(task_struct_ptr_t)

        # Offset of `tasks` list_head inside struct task_struct
        offset = int(gdb.parse_and_eval(
            "(unsigned long)&((struct task_struct *)0)->tasks"
        ))

        print(f"{'TASK':>18} {'CRED':>18} {'UID':>6} {'PID':>6} {'PPID':>6} CMD")

        task = init_task

        active_cpu = current_tasks_by_cpu()
        
        while True:
            t = task.dereference()

            pid = int(t["pid"])

            # parent may be null for early tasks
            parent = t["real_parent"]
            ppid = int(parent.dereference()["pid"]) if parent else 0
            
            cred = t["cred"]
            uid = int(cred.dereference()['uid']['val'])
            
            try:
                comm = t["comm"].string()
            except:
                comm = "<unknown>"
    
            curr_cpu = f'    (cpu={active_cpu[int(task)]})' if int(task) in active_cpu else ''

            print(f"{int(task):>#18x} {int(cred):>#18x} {uid:6} {pid:6} {ppid:6} {comm}{curr_cpu}")

            # Move to next task in circular list
            next_task = t["tasks"]["next"]

            task = (next_task.cast(gdb.lookup_type("char").pointer()) - offset).cast(
                task_struct_ptr_t
            )

            if task == init_task:
                break


ShowTaskCreds()
KernelPs()
