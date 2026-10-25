"""Candidate code runs only in disposable resource-limited containers."""
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

IMAGE = os.getenv('RUNNER_IMAGE', 'interviewace-runner:local')


LANGUAGES = {
    'python': ('solution.py', ['python', '-I', '-B', '/work/solution.py']),
    'javascript': ('solution.js', ['node', '/work/solution.js']),
    'c': ('solution.c', ['sh', '-c', 'gcc /work/solution.c -O2 -o /tmp/solution && /tmp/solution']),
    'cpp': ('solution.cpp', ['sh', '-c', 'g++ /work/solution.cpp -O2 -std=c++17 -o /tmp/solution && /tmp/solution']),
}


def execute(source: str, tests: list[dict], language: str = 'python') -> dict:
    if os.getenv('ENABLE_CODE_EXECUTION', 'true').lower() != 'true':
        raise RuntimeError('Code execution is disabled in this deployment.')
    if language not in LANGUAGES:
        raise ValueError('Unsupported code language.')
    filename, runtime = LANGUAGES[language]
    results = []
    with tempfile.TemporaryDirectory(prefix='interviewace-code-') as directory:
        Path(directory, filename).write_text(source, encoding='utf-8')
        for case in tests:
            name = 'ia-' + uuid4().hex
            command = ['docker', 'run', '--rm', '--pull=never', '--name', name,
                       '--network=none', '--read-only', '--memory=128m', '--memory-swap=128m',
                       '--cpus=0.5', '--pids-limit=32', '--cap-drop=ALL',
                       '--security-opt=no-new-privileges', '--user=65534:65534',
                       '--ulimit', 'cpu=2:2', '--ulimit', 'fsize=65536:65536',
                       '--tmpfs', '/tmp:rw,nosuid,size=8m', '--log-driver=none',
                       '--mount', f'type=bind,source={directory},target=/work,readonly',
                       '-i', IMAGE, *runtime]
            try:
                # Files rather than PIPE prevent unbounded output consuming API memory.
                with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output, stderr=errors)
                    try:
                        process.communicate(case['input'].encode(), timeout=8)
                    except subprocess.TimeoutExpired:
                        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=5)
                        process.kill()
                        process.wait(timeout=5)
                        results.append({'passed': False, 'status': 'timeout', 'output': '', 'error': 'Execution timed out.'})
                        continue
                    output.seek(0); errors.seek(0)
                    stdout = output.read(16000).decode(errors='replace')
                    stderr = errors.read(8000).decode(errors='replace')
                if process.returncode == 125:
                    raise RuntimeError('Code sandbox unavailable. Build the runner image and start Docker.')
                passed = process.returncode == 0 and stdout.strip() == case['expected'].strip()
                if passed:
                    status = 'passed'
                elif process.returncode == 0:
                    status = 'wrong_answer'
                elif language in ('c', 'cpp') and ('error:' in stderr.lower() or 'undefined reference' in stderr.lower()):
                    status = 'compile_error'
                else:
                    status = 'runtime_error'
                results.append({'passed': passed, 'status': status, 'output': stdout, 'error': stderr,
                                'expected': case['expected']})
            except FileNotFoundError as exc:
                raise RuntimeError('Docker is required for code execution; host execution is disabled.') from exc
    return {'tests': results, 'passed': sum(r['passed'] for r in results), 'total': len(results)}
