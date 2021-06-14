# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
    name: custom
    type: stdout
    short_description: custom Ansible screen output
    description:
      - custom Ansible callback based on the default one
    extends_documentation_fragment:
      - default_callback
'''
import os
import json
import time

from ansible import constants as C
from ansible.utils.color import stringc
from ansible.plugins.callback import (module_response_deepcopy,
                                      strip_internal_keys)
from ansible.plugins.callback.default import CallbackModule as Default

# from ansible.plugins.callback import CallbackBase

class CallbackModule(Default):

    '''
    This is the default callback interface, which simply prints messages
    to stdout when new callback events are received.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'custom'

    _task_counter = 0
    _task_total = 0

    _task_execution_time_start_time = time.time()

    def _display_cmd_output(self, processed_result):
        play_is_running_on_github = os.environ.get('GITHUB_ACTIONS', False)

        if play_is_running_on_github:
            self._display.display("::group::%s" % processed_result['cmd'])
        else:
            self._display.display("$ %s" % processed_result['cmd'])

        if processed_result.get('stdout'):
            self._display.display(str(processed_result['stdout']))
        if processed_result.get('stderr'):
            self._display.display(str(processed_result['stderr']), color=C.COLOR_ERROR)

        if play_is_running_on_github:
            self._display.display("::endgroup::")

    def _display_task_banner(self, task, status, color):
        args = ''

        if not task.no_log and C.DISPLAY_ARGS_TO_STDOUT:
            args = ', '.join(('%s=%s' % a for a in task.args.items()))
            args = ' %s' % args

        task_header = "%d/%d" % (self._task_counter, self._task_total)
        task_execution_time = f"{self._get_time_from_task_start():.0f}s"

        self._display.display("\n[%s] %s %s%s (%s)" % (
            stringc(status, color),
            task_header,
            task.get_name().strip(),
            args,
            task_execution_time,
        ))

    def _display_task_result(self, result, status, color):
        self._display_task_banner(result._task, status, color)

        self._handle_exception(result._result)
        self._handle_warnings(result._result)
        self._clean_results(result._result, result._task.action)

        action = result._task.action
        processed_result = self._process_results(result._result)

        if 'censored' in processed_result:
            self._display.display("censored: %s" % processed_result['censored'], color=C.COLOR_VERBOSE)
        else:
            if action in('command', 'ansible.builtin.shell', 'shell'):
                if processed_result.get('cmd'):
                    self._display_cmd_output(processed_result)
            else:
                self._display.display("[%s]\n%s" % (action, json.dumps(processed_result, indent=4)))

    def _process_results(self, result, indent=None, sort_keys=True, keep_invocation=False):
        if result.get('_ansible_no_log', False):
            return json.dumps(dict(censored="The output has been hidden due to the fact that 'no_log: true' was specified for this result"))

        # All result keys stating with _ansible_ are internal, so remove them from the result before we output anything.
        abridged_result = strip_internal_keys(module_response_deepcopy(result))

        return abridged_result

    def _task_execution_time_start_measuring(self):
        self._task_execution_time_start_time = time.time()

    def _get_time_from_task_start(self):
        current_time = time.time()
        time_diff = current_time - self._task_execution_time_start_time

        return time_diff

    def _task_execution_time_stop_and_display_results(self):
        current_time = time.time()
        execution_time = current_time - self._task_execution_time_start_time

        self._display.display(f"TIME: {execution_time:.0f}s")

    def v2_runner_on_start(self, host, task):
        pass

    def v2_playbook_on_play_start(self, play):
        super().v2_playbook_on_play_start(play)
        self._task_total = len(self._play.get_tasks()[0])

    # Tasks

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_execution_time_start_measuring()
        self._task_counter += 1

    def v2_runner_on_ok(self, result):
        self._display_task_result(result, status="OK", color=C.COLOR_OK)

    def v2_runner_on_unreachable(self, result):
        self._display_task_result(result, status="UNREACHABLE", color=C.COLOR_UNREACHABLE)

    def v2_runner_on_skipped(self, result):
        self._display_task_result(result, status="SKIPPED", color=C.COLOR_SKIP)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._display_task_result(result, status="FAILED", color=C.COLOR_ERROR)

    # Subtasks

    def v2_runner_item_on_ok(self, result):
        return super().v2_runner_item_on_ok(result)

    def v2_runner_item_on_failed(self, result):
        return super().v2_runner_item_on_failed(result)

    def v2_runner_item_on_skipped(self, result):
        return super().v2_runner_item_on_skipped(result)
