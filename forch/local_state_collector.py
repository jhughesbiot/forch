"""Collecting the states of the local system"""

import copy
from datetime import datetime
import logging
import re
import threading

import psutil

import forch.constants as constants

LOGGER = logging.getLogger('localstate')

class LocalStateCollector:
    """Storing local system states"""

    def __init__(self, config, process_interval: int = 60):
        self._state = {'processes': {}}
        self._process_state = self._state['processes']
        self._target_procs = config.get('processes', {})
        self._current_time = None
        self._process_interval = process_interval
        self._process_lock = threading.Lock()

    def initialize(self):
        """Initialize LocalStateCollector"""
        self.start_process_loop()

    def get_process_summary(self):
        """Return a summary of process table"""
        process_state = self.get_process_state()
        return {
            'state': process_state.get('processes_state'),
            'detail': process_state.get('processes_state_detail')
        }

    def get_process_state(self):
        """Get the states of processes"""
        process_state = None
        with self._process_lock:
            process_state = copy.deepcopy(self._process_state)
        return process_state

    def _get_process_info(self):
        """Get the raw information of processes"""

        process_state = {}
        procs = self._get_target_processes()
        broken = []

        # fill up process info
        for target_name, target_map in self._target_procs.items():
            state_map = {}
            process_state[target_name] = state_map
            if target_name not in procs:
                continue
            proc_list = procs[target_name]
            target_count = int(target_map.get('count', 1))
            if len(proc_list) == target_count:
                state_map.update(self._extract_process_state(target_name, proc_list))
                state_map['state'] = constants.STATE_HEALTHY
            else:
                state_map['state'] = 'broken'
                err_detail = f"Process {target_name}: number of process ({len(proc_list)}) " \
                             f"does not match target count ({target_count})"
                state_map['detail'] = err_detail
                LOGGER.error(err_detail)
                broken.append(target_name)

        state = constants.STATE_BROKEN if broken else constants.STATE_HEALTHY
        process_state['processes_state'] = state
        process_state['processes_state_last_update'] = self._current_time
        process_state['processes_state_detail'] = ', '.join(broken)
        if state != self._process_state.get('processes_state'):
            process_state['processes_state_last_change'] = self._current_time
            state_change_count = self._process_state.get('processes_state_change_count', 0) + 1
            process_state['processes_state_change_count'] = state_change_count

        self._process_state = process_state

    def _get_target_processes(self):
        """Get target processes"""
        procs = {}
        for target_name, target_map in self._target_procs.items():
            target_regex = target_map['regex']
            proc_list = procs.setdefault(target_name, [])

            for proc in psutil.process_iter():
                cmd_line_str = ' '.join(proc.cmdline())
                if re.search(target_regex, cmd_line_str):
                    proc_list.append(proc)

        return procs

    def _extract_process_state(self, proc_name, proc_list):
        """Fill process state for a single process"""
        proc_map = {}
        old_proc_map = self._process_state.get(proc_name, {})

        proc_map['cmd_line'] = ' '.join(proc_list[0].cmdline())
        create_time = max(proc.create_time() for proc in proc_list)
        proc_map['create_time'] = datetime.fromtimestamp(create_time).isoformat()
        proc_map['create_time_last_update'] = self._current_time

        if proc_map['create_time'] != old_proc_map.get('create_time'):
            proc_map['create_time_last_change'] = self._current_time
            create_time_change_count = old_proc_map.get('create_time_change_count', 0) + 1
            proc_map['create_time_change_count'] = create_time_change_count

        cpu_time_user = 0.0
        cpu_time_system = 0.0
        cpu_time_iowait = None
        memory_rss = 0.0
        memory_vms = 0.0

        for proc in proc_list:
            cpu_time_user += proc.cpu_times().user
            cpu_time_system += proc.cpu_times().system
            if hasattr(proc.cpu_times(), 'iowait'):
                if not cpu_time_iowait:
                    cpu_time_iowait = 0.0
                cpu_time_iowait += proc.cpu_times().iowait

            memory_rss += proc.memory_info().rss / 1e6
            memory_vms += proc.memory_info().vms / 1e6

        proc_map['cpu_times_s'] = {}
        proc_map['cpu_times_s']['user'] = cpu_time_user / len(proc_list)
        proc_map['cpu_times_s']['system'] = cpu_time_system / len(proc_list)
        if cpu_time_iowait:
            proc_map['cpu_times_s']['iowait'] = cpu_time_iowait / len(proc_list)

        proc_map['memory_info_mb'] = {}
        proc_map['memory_info_mb']['rss'] = memory_rss / len(proc_list)
        proc_map['memory_info_mb']['vms'] = memory_vms / len(proc_list)

        return proc_map

    def _periodic_get_process_info(self):
        """Periodically gather the processes info"""
        with self._process_lock:
            self._current_time = datetime.now().isoformat()
            self._get_process_info()
        threading.Timer(self._process_interval, self._periodic_get_process_info).start()

    def start_process_loop(self):
        """Start a loop to periodically gather the processes info"""
        threading.Thread(target=self._periodic_get_process_info).start()