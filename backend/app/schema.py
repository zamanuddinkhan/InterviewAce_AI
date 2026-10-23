"""Idempotent additive migrations for existing accounts and interviews."""
from sqlalchemy import inspect, text


def upgrade(engine):
    with engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('users')}
        for name, length in [('first_name', 50), ('last_name', 50), ('contact_number', 16)]:
            if name not in columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} VARCHAR({length}) NOT NULL DEFAULT ''"))
        rows = connection.execute(text("SELECT id, name FROM users WHERE first_name = ''")).all()
        for identifier, name in rows:
            first, _, last = name.strip().partition(' ')
            connection.execute(text('UPDATE users SET first_name=:first, last_name=:last WHERE id=:id'),
                               {'first': first[:50], 'last': last[:50], 'id': identifier})
        # Legacy contact numbers remain empty: never invent personal data.
        if inspect(connection).has_table('interviews'):
            interview_columns = {column['name'] for column in inspect(connection).get_columns('interviews')}
            if 'custom_kind' not in interview_columns:
                connection.execute(text('ALTER TABLE interviews ADD COLUMN custom_kind VARCHAR(100) NULL'))
