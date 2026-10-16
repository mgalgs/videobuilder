"""Community-submitted capabilities: a creator points the editor at an X post
showing a technique, the builder makes an original demo plus a catalog entry
and reference doc in a reserved `capabilities/<slug>` project, and an admin
publishes or rejects it. This module is a leaf: it must not import `library`,
`accounts` or `editor` at module level (library.py imports this module, and
accounts.py explains the same cycle for its own reason)."""

NAMESPACE = 'capabilities'


def is_reserved(name):
    """Whether `name` -- a library project name, or a bare username -- collides
    with the reserved namespace every community capability lives under:
    `capabilities` itself, or any `capabilities/<x>`."""
    return isinstance(name, str) and (name == NAMESPACE or name.startswith(NAMESPACE + '/'))
