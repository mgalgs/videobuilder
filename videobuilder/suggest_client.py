"""A client for one OpenAI-compatible chat endpoint (OpenRouter, Anthropic's
compatible endpoint, a local vLLM or llama.cpp), used by the suggest layer
(suggest.py) to ask one question per paused note: what in the catalog fits
what the director just typed. Configured with a base URL, a model and a key;
the key is never put in a request log, an exception message or a response --
see Suggest.ask, which is the only thing that ever calls this.

Cancellation: `complete(..., cancel_event=...)` starts a second thread that
waits on a `threading.Event` and closes the connection the moment it is set,
the same way a browser's AbortController stops a `fetch` mid-flight; a
request nobody cancels still gives up after `timeout` seconds regardless
(the socket's own timeout), so a slow or wedged endpoint never blocks a
director's typing for long.
"""
import http.client
import json
import re
import socket
import threading
from urllib.parse import urlsplit

DEFAULT_MODEL = 'anthropic/claude-haiku-5.5'
# "About 8 s" per the design notes: a slow endpoint must give up silently well
# before a director would notice the note box feels stuck.
TIMEOUT = 8.0
MAX_BYTES = 1 << 20


class SuggestError(Exception):
    """The endpoint could not be reached, or answered with something unusable."""


class SuggestCancelled(SuggestError):
    """`cancel_event` fired before an answer came back."""


def check_suggest_url(url):
    """--suggest-url, without a trailing slash; ValueError unless it is a
    plain http(s) URL with a host and no credentials, query or fragment
    (the same shape pictures.check_base_url requires of --artbox-url)."""
    if not isinstance(url, str):
        raise ValueError('--suggest-url must be a URL')
    parts = urlsplit(url.strip())
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment):
        raise ValueError('--suggest-url must be a plain http(s) URL, like https://openrouter.ai/api/v1')
    return url.strip().rstrip('/')


class SuggestClient:
    """A client for one base URL, model and key. `complete` makes one chat
    completion call, asked for JSON only, and returns (answer, usage)."""

    def __init__(self, base_url, model=None, key=None, timeout=TIMEOUT):
        self.base_url = check_suggest_url(base_url)
        self.model = model or DEFAULT_MODEL
        self.key = key
        self.timeout = timeout

    def _connection(self):
        parts = urlsplit(self.base_url)
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        cls = http.client.HTTPSConnection if parts.scheme == 'https' else http.client.HTTPConnection
        return cls(parts.hostname, port, timeout=self.timeout), parts.path.rstrip('/')

    def _body(self, static_block, video_block, user_text, max_tokens):
        # Two system blocks (see suggest.py): the static catalog, marked for
        # prompt caching on a provider that passes `cache_control` through
        # (OpenRouter does, for an Anthropic model); then the per-video one,
        # which changes with the film and so is never marked cached here.
        return {
            'model': self.model, 'temperature': 0, 'max_tokens': max_tokens,
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': [{'type': 'text', 'text': static_block,
                                                'cache_control': {'type': 'ephemeral'}}]},
                {'role': 'system', 'content': video_block},
                {'role': 'user', 'content': user_text},
            ],
        }

    def complete(self, static_block, video_block, user_text, *, max_tokens=400, cancel_event=None):
        """(answer, usage): `answer` is the assistant's reply parsed as JSON
        (whatever shape it answered; suggest.py validates it), `usage` is the
        endpoint's own `{"prompt_tokens", "completion_tokens", ...}` or None.
        Raises SuggestError on any failure to reach or parse an answer, or
        SuggestCancelled if `cancel_event` fired first."""
        conn, path = self._connection()
        if cancel_event is not None:
            def watch():
                # A plain close() from another thread doesn't reliably break a
                # concurrent blocking recv() on Linux; shutdown() does.
                if cancel_event.wait(self.timeout) and conn.sock is not None:
                    try:
                        conn.sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
            threading.Thread(target=watch, daemon=True).start()
        try:
            body = json.dumps(self._body(static_block, video_block, user_text, max_tokens)).encode()
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
                       'User-Agent': 'videobuilder-suggest/1'}
            if self.key:
                headers['Authorization'] = f'Bearer {self.key}'
            conn.request('POST', path + '/chat/completions', body=body, headers=headers)
            resp = conn.getresponse()
            payload = resp.read(MAX_BYTES + 1)
            status = resp.status
        except Exception as exc:
            if cancel_event is not None and cancel_event.is_set():
                raise SuggestCancelled('cancelled') from None
            raise SuggestError(f'{exc}') from None
        finally:
            conn.close()
        if cancel_event is not None and cancel_event.is_set():
            raise SuggestCancelled('cancelled')
        if len(payload) > MAX_BYTES:
            raise SuggestError(f'response over {MAX_BYTES} bytes')
        if status != 200:
            detail = payload[:200].decode('utf-8', 'replace')
            raise SuggestError(f'HTTP {status} from the suggest endpoint: {detail}')
        try:
            data = json.loads(payload)
            content = data['choices'][0]['message']['content']
            if isinstance(content, list):
                content = ''.join(p.get('text', '') for p in content if isinstance(p, dict))
            # Some models wrap the JSON in a ```json fence despite response_format.
            content = re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '', content)
            answer = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError):
            raise SuggestError('the suggest endpoint answered something unusable') from None
        usage = data.get('usage') if isinstance(data.get('usage'), dict) else None
        return answer, usage
