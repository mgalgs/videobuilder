"""The one git subprocess runner shared by the editor's working-tree git calls
and the library's bare-repo management.

`hooks=True` (the default) adds `-c core.hooksPath=/dev/null`, as every call
against the editor's own checkout has always done. The library's bare-repo
calls (creating a repo, cloning one, writing an object with `--git-dir`) never
had that flag and must not gain it: pass `hooks=False` there.

`binary=True` reads stdout/stderr as raw bytes instead of decoding them as
text: use it for a blob whose content isn't known to be UTF-8 (e.g. `git show
main:<path>` for an arbitrary file in a repo), so that content a caller can't
control doesn't raise UnicodeDecodeError out of subprocess.run itself.
"""
import subprocess


def git(root, *args, check=True, input=None, env=None, git_dir=None, hooks=True, binary=False):
    argv = ['git']
    if hooks:
        argv += ['-c', 'core.hooksPath=/dev/null']
    if git_dir is not None:
        argv += ['--git-dir', str(git_dir)]
    argv += list(args)
    if not binary and isinstance(input, bytes):
        input = input.decode()
    result = subprocess.run(argv, cwd=root, input=input, env=env, capture_output=True, text=not binary)
    if check and result.returncode:
        stderr, stdout = result.stderr, result.stdout
        if binary:
            stderr, stdout = stderr.decode('utf-8', 'replace'), stdout.decode('utf-8', 'replace')
        raise ValueError(stderr.strip() or stdout.strip())
    if not check:
        return result
    return result.stdout.strip(b' \t\r\n') if binary else result.stdout.strip()
