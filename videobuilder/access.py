"""Per-project access: one JSON file under the library state dir mapping a
project name to its owner and collaborators, written atomically under a
lock. A project absent from the file has no recorded owner: an admin is its
implied owner (every project predating auth, say).

Each grant records the uid of the account it was issued to, not just its
username (see accounts.Accounts.uid). `get` drops a grant whose holder's
account no longer exists or was recreated under the same name since the
grant was made, so deleting an account and letting someone else sign up
under its old name never hands them the old account's projects."""
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

    def get(self, name, accounts):
        record = self._load().get(name) or {'owner': None, 'collaborators': []}
        owner = record['owner']
        if owner is not None and accounts.uid(owner) != record.get('owner_uid'):
            owner = None
        collaborators = [c['username'] for c in record['collaborators']
                         if accounts.uid(c['username']) == c['uid']]
        return {'owner': owner, 'collaborators': collaborators}

    def set_owner(self, name, owner, accounts):
        with self.lock:
            data = self._load()
            data[name] = {'owner': owner, 'owner_uid': accounts.uid(owner), 'collaborators': []}
            self._save(data)

    def can_access(self, name, username, accounts):
        if accounts.is_admin(username):
            return True
        if username is None:
            return False
        record = self.get(name, accounts)
        return username == record['owner'] or username in record['collaborators']

    def can_share(self, name, username, accounts):
        if accounts.is_admin(username):
            return True
        return username is not None and username == self.get(name, accounts)['owner']

    def invite(self, name, username, accounts):
        with self.lock:
            data = self._load()
            record = data.setdefault(name, {'owner': None, 'owner_uid': None, 'collaborators': []})
            uid = accounts.uid(username)
            is_owner = username == record['owner'] and record.get('owner_uid') == uid
            # Drop any stale entry for this username (a different, deleted account held
            # it) so a recreated account can be invited back instead of silently no-oping.
            record['collaborators'] = [c for c in record['collaborators']
                                       if c['username'] != username or c['uid'] == uid]
            if not is_owner and not any(c['username'] == username for c in record['collaborators']):
                record['collaborators'].append({'username': username, 'uid': uid})
            self._save(data)

    def remove(self, name, username):
        with self.lock:
            data = self._load()
            record = data.get(name)
            if record:
                kept = [c for c in record['collaborators'] if c['username'] != username]
                if len(kept) != len(record['collaborators']):
                    record['collaborators'] = kept
                    self._save(data)
