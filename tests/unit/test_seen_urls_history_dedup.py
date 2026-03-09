import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import storage_service


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table_name, supabase):
        self.table_name = table_name
        self.supabase = supabase
        self._urls = None
        self._rows_to_upsert = None

    def select(self, _columns):
        return self

    def limit(self, _value):
        return self

    def in_(self, _column, urls):
        self._urls = urls
        return self

    def upsert(self, rows):
        self._rows_to_upsert = rows
        return self

    def execute(self):
        if self.table_name != 'seen_urls':
            raise AssertionError('unexpected table')

        if self._rows_to_upsert is not None:
            self.supabase.upserted_rows.extend(self._rows_to_upsert)
            return FakeResponse(self._rows_to_upsert)

        if self._urls is None:
            return FakeResponse([])

        data = [
            {'canonical_url': canonical_url}
            for canonical_url in self._urls
            if canonical_url in self.supabase.existing_urls
        ]
        return FakeResponse(data)


class FakeSupabase:
    def __init__(self, existing_urls):
        self.existing_urls = set(existing_urls)
        self.upserted_rows = []

    def table(self, table_name):
        return FakeQuery(table_name, self)


def test_filter_new_urls_for_history_dedup_filters_existing_urls(monkeypatch):
    fake_supabase = FakeSupabase(existing_urls={'github.com/org/existing'})
    monkeypatch.setattr(storage_service.supabase_client, 'get_supabase_client', lambda: fake_supabase)
    monkeypatch.setattr(storage_service, '_seen_urls_table_probe_completed', True)
    monkeypatch.setattr(storage_service, '_seen_urls_table_is_available', True)

    new_urls = storage_service.filter_new_urls_for_history_dedup(
        source_id='github_trending',
        first_seen_date='2026-03-08',
        canonical_urls=[
            'github.com/org/existing',
            'github.com/org/new',
            'github.com/org/new',
        ],
    )

    assert new_urls == {'github.com/org/new'}
    assert fake_supabase.upserted_rows == [
        {
            'canonical_url': 'github.com/org/new',
            'source_id': 'github_trending',
            'first_seen_date': '2026-03-08',
        }
    ]


def test_filter_new_urls_for_history_dedup_returns_input_when_table_unavailable(monkeypatch):
    monkeypatch.setattr(storage_service, '_probe_seen_urls_table_once', lambda: False)

    new_urls = storage_service.filter_new_urls_for_history_dedup(
        source_id='github_trending',
        first_seen_date='2026-03-08',
        canonical_urls=['github.com/org/one', 'github.com/org/two'],
    )

    assert new_urls == {'github.com/org/one', 'github.com/org/two'}
