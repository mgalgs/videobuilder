"""Per-project access: one JSON file under the library state dir mapping a
project name to its owner and collaborators, written atomically under a
lock. A project absent from the file has no recorded owner: an admin is its
implied owner (every project predating auth, say)."""
import json
import os
import threading


class Access:
    def __init__(self, state_dir):
        self.path = os.path.join(state_dir, 'access.json')
        self.lock = threading.RLock()

    def _load(self):
        try:
            with open(self.path, encoding='utf-8') as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {}

    def _save(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh)
        os.replace(tmp, self.path)

    def get(self, name):
        return self._load().get(name) or {'owner': None, 'collaborators': []}

    def set_owner(self, name, owner):
        with self.lock:
            data = self._load()
            data[name] = {'owner': owner, 'collaborators': []}
            self._save(data)

    def can_access(self, name, username, accounts):
        if accounts.is_admin(username):
            return True
        if username is None:
            return False
        record = self.get(name)
        return username == record['owner'] or username in record['collaborators']

    def can_share(self, name, username, accounts):
        if accounts.is_admin(username):
            return True
        return username is not None and username == self.get(name)['owner']

    def invite(self, name, username):
        with self.lock:
            data = self._load()
            record = data.setdefault(name, {'owner': None, 'collaborators': []})
            if username != record['owner'] and username not in record['collaborators']:
                record['collaborators'].append(username)
            self._save(data)

    def remove(self, name, username):
        with self.lock:
            data = self._load()
            record = data.get(name)
            if record and username in record['collaborators']:
                record['collaborators'].remove(username)
                self._save(data)
