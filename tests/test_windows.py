import subprocess

from claude_scheduler.platforms.windows import WindowsTaskBackend


class FakeTaskScheduler:
    def __init__(self, query_output=""):
        self.query_output = query_output
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[1] == "/Query":
            return subprocess.CompletedProcess(command, 0, self.query_output, "")
        return subprocess.CompletedProcess(command, 0, "", "")


def test_windows_install_removes_old_tasks_and_creates_each_time():
    process = FakeTaskScheduler(
        '"\\Claude_0730","N/A","Ready"\n'
        '"\\Unrelated","N/A","Ready"\n'
    )
    backend = WindowsTaskBackend(process)

    backend.install([r"C:\Program Files\ccs.exe"], ("07:00", "12:05"))

    delete_calls = [call for call, _ in process.calls if call[1] == "/Delete"]
    create_calls = [call for call, _ in process.calls if call[1] == "/Create"]
    assert len(delete_calls) == 1
    assert delete_calls[0][3] == r"\Claude_0730"
    assert len(create_calls) == 2
    assert create_calls[0][create_calls[0].index("/TN") + 1] == "ClaudeScheduler_0700"
    action = create_calls[0][create_calls[0].index("/TR") + 1]
    assert action == r'"C:\Program Files\ccs.exe" run'


def test_windows_status_ignores_unrelated_tasks():
    process = FakeTaskScheduler('"\\Unrelated","N/A","Ready"\n')

    assert WindowsTaskBackend(process).status() == (False, "Task Scheduler")
