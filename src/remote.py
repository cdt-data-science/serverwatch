#!/usr/bin/python

from collections import defaultdict, namedtuple
import subprocess
from os import getenv, popen
import re
from math import ceil
import json
from datetime import datetime


USER = getenv('DICE_USER', None)
CMD_SSH_PRIM = USER + "@{}"
PATH_DATA = '/home/matt/documents/serverwatch/data/'


class RemoteStats(object):

    KEY_GPU = 'gpu'
    KEY_CPU = 'cpu'
    KEY_GPU_INFO = 'gpuinfo'

    CMD_SSH = ["ssh", "-K", "-oStrictHostKeyChecking=no"]
    CMD_SSH_ID = CMD_SSH_PRIM.format

    CMD_NVIDIA_UTIL = "'nvidia-smi -q'"
    CMD_PS = "'ps -eo pcpu,pid,user,args --no-headers| sort -t. -nk1,2 -k4,4 -r | head -n 5'"
    CMD_W = "'w'"
    CMD_FINGER = "'finger {}'".format
    CMD_TOP = "'top -b -n 1 -u !root -o %CPU'"
    CMD_GROUPS = "'groups {}'".format

    IDX_TOP_USER = 1
    IDX_TOP_CPU = 8
    IDX_TOP_MEM = 9
    IDX_TOP_TIME = 10
    IDX_TOP_CMD = 11

    TUPLE_GPU = namedtuple('GPUInfo', ['model', 'ram_used', 'ram_total', 'ram_pc', 'utilization'])

    PATTERN_NVIDA = re.compile(r"(\d+)(?=MiB.*\%)")

    INTERVAL = 15 * 60

    SERVERS = {
        'charles': range(1, 11),
        # 'james': range(1, 22),
        # 'mary': None
    }

    def __init__(self):
        self._stats = defaultdict(dict)
        self._users = {}
        self._cdt_users = {}
        self._last_update = None

    def __run_shell(self, cmd):
        return subprocess.check_output(cmd)

    def __run_popen(self, cmd):
        pro = popen(" ".join(cmd))
        pre = pro.read()
        pro.close()

        return pre

    def _finger_user(self, user):
        if user not in self._users:
            cmd_finger = self.CMD_SSH[:]
            cmd_finger.append(self.CMD_SSH_ID('staff.compute'))
            cmd_finger.append(self.CMD_FINGER(user))

            data = self.__run_popen(cmd_finger).split('\n')[0].split('Name:')[1]

            username = data.strip()
            self._users[user] = username

        return self._users[user]

    def _is_cdt_user(self, user):
        if user not in self._cdt_users:
            cmd_groups = self.CMD_SSH[:]
            cmd_groups.append(self.CMD_SSH_ID('staff.compute'))
            cmd_groups.append(self.CMD_GROUPS(user))

            data = self.__run_popen(cmd_groups)

            self._cdt_users[user] = 'cdt' in data

        return self._cdt_users[user]

    def _process_cpu_data(self, cpu):
        parsed = []

        for line in cpu:
            parts = line.split()

            if len(parts) == 0 or parts[self.IDX_TOP_CMD] == 'top' or float(parts[self.IDX_TOP_MEM]) <= 0.1:
                continue

            tup = (
                parts[self.IDX_TOP_USER],
                self._finger_user(parts[self.IDX_TOP_USER]),
                parts[self.IDX_TOP_CMD],
                parts[self.IDX_TOP_CPU],
                parts[self.IDX_TOP_MEM],
                parts[self.IDX_TOP_TIME],
                self._is_cdt_user(parts[self.IDX_TOP_USER])
            )

            parsed.append(tup)

        return parsed

    def __commit_gpu_data(self, server_name, model, ram_used, ram_total, ram_pc, utilization):
        if self.KEY_GPU_INFO not in self._stats[server_name]:
            self._stats[server_name][self.KEY_GPU_INFO] = []

        self._stats[server_name][self.KEY_GPU_INFO].append(
            self.TUPLE_GPU(model, ram_used, ram_total, ram_pc, utilization)
        )

    def __update_gpu_info(self, server_name):
        cmd_gpu = self.CMD_SSH[:]
        cmd_gpu.append(self.CMD_SSH_ID(server_name))
        cmd_gpu.append(self.CMD_NVIDIA_UTIL)
        gpu_data = self.__run_popen(cmd_gpu).split('\n')

        delim = ' : '
        parsed = []

        found_gpu = False
        found_product = False
        found_fb = False
        found_utilization = False

        derived = {}

        for line in gpu_data:
            line = line.strip()

            if not found_gpu and line.startswith('GPU'):
                found_gpu = True
            elif not found_product and line.startswith('Product Name'):
                found_product = True
                derived['model'] = line.split(delim)[1]
            elif not found_fb and line.startswith('FB Memory Usage'):
                found_fb = True
            elif found_fb and line.startswith('Total') and 'ram_total' not in derived:
                derived['ram_total'] = int(line.split(delim)[1].split()[0])
            elif found_fb and line.startswith('Used') and 'ram_pc' not in derived:
                derived['ram_used'] = int(line.split(delim)[1].split()[0])
                derived['ram_pc'] = int(ceil((float(derived['ram_used'])/derived['ram_total'])*100))
            elif not found_utilization and line.startswith('Utilization'):
                found_utilization = True
            elif found_utilization and line.startswith('Gpu'):
                derived['utilization'] = int(line.split(delim)[1].split()[0])
            elif found_utilization and line.startswith('Memory'):
                self.__commit_gpu_data(server_name, **derived)
                derived.clear()
                found_fb = found_gpu = found_product = found_utilization = False

    def __update_cpu_processes(self, server_name):
        cmd_cpu = self.CMD_SSH[:]
        cmd_cpu.append(self.CMD_SSH_ID(server_name))
        cmd_cpu.append(self.CMD_TOP)

        cpu_data = self.__run_popen(cmd_cpu).split('\n')[7:]
        cpu_data = self._process_cpu_data(cpu_data)

        self._stats[server_name][self.KEY_CPU] = cpu_data

    def update_stats(self):
        self.save_stats()
        self._stats.clear()

        for k, v in self.SERVERS.iteritems():
            if v is None:
                pass
            else:
                for v_i in v:
                    server_name = "{}{:02d}".format(k, v_i)

                    if k == 'charles':
                        self.__update_gpu_info(server_name)

                    self.__update_cpu_processes(server_name)

        self._last_update = datetime.now()

    def save_stats(self):
        with open(PATH_DATA + 'watchatron_{}.json'.format(datetime.now()), 'w') as fp:
            json.dump(self._stats, fp)

    def should_update(self):
        if len(self._stats.keys()) == 0 or self._last_update is None:
            return True

        delta = datetime.now() - self._last_update
        return delta.total_seconds() >= self.INTERVAL

    def get_stats(self):
        if self.should_update():
            self.update_stats()

        return self._stats

    def pprint(self):
        for k, v in self._stats.iteritems():
            print(k)

            for k_i, v_j in v.iteritems():
                print("{}:{}".format(k_i, v_j))

    def get_time_updated(self):
        return self._last_update.isoformat() if self._last_update is not None else ''


class LocalStats(object):

    KEY_CURRENT = 'current'
    KEY_USERS = 'users'
    KEY_RATIO = 'ratio'

    def __init__(self, stats):
        self.stats = stats
        self.servers = sorted(stats.keys())
        self.current_processes = defaultdict(int)
        self.current_share = defaultdict(int)
        self.users = defaultdict(list)
        self.proportions = []

    def __load_local_files(self):
        pass

    def __generate_current_user_share(self):
        self.current_processes.clear()
        self.current_share.clear()
        self.users.clear()
        self.proportions = [0, 0]

        total_proc = 0

        for server in self.servers:
            curr = self.stats[server][RemoteStats.KEY_CPU]

            for entry in curr:
                user = entry[0]

                if user not in self.users:
                    self.users[user] = [entry[1], entry[6]]

                if entry[6]:
                    self.proportions[0] += 1
                else:
                    self.proportions[1] += 1

                total_proc += 1
                self.current_processes[user] += 1

        for user, n_processes in self.current_processes.iteritems():
            self.current_share[user] = (float(n_processes) / total_proc) * 100

        self.proportions = [(float(x) / len(self.users.keys())) * 100 for x in self.proportions]

    def __generate_historic_user_share(self):
        pass

    def get_stats(self):
        self.__generate_current_user_share()

        return {
            self.KEY_CURRENT: self.current_share,
            self.KEY_USERS: self.users,
            self.KEY_RATIO: self.proportions
        }


if __name__ == '__main__':
    if USER is None:
        print('Need to set environment variable $DICE_USER')
    else:
        r = RemoteStats()
        r.update_stats()
        r.pprint()
