"""The one git subprocess runner shared by the editor's working-tree git calls
and the library's bare-repo management.

`hooks=True` (the default) adds `-c core.hooksPath=/dev/null`, as every call
against the editor's own checkout has always done. The library's bare-repo
calls (creating a repo, cloning one, writing an object with `--git-dir`) never
had that flag and must not gain it: pass `hooks=False` there.
"""
import subprocess


def git(root, *args, check=True, input=None, env=None, git_dir=None, hooks=True):
    argv = ['git']
    if hooks:
        argv += ['-c', 'core.hooksPath=/dev/null']
    if git_dir is not None:
        argv += ['--git-dir', str(git_dir)]
    argv += list(args)
    if isinstance(input, bytes):
        input = input.decode()
    result = subprocess.run(argv, cwd=root, input=input, env=env, capture_output=True, text=True)
    if check and result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip() if check else result
