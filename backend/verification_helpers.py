"""Synthetic account payloads for automated and live verification only."""
from uuid import uuid4


def registration(email=None, password=None):
    password = password or ('Study-' + uuid4().hex + '-A7!')
    return {'first_name':'Test', 'last_name':'Student', 'contact_number':'+919876543210',
            'email':email or (uuid4().hex+'@example.com'), 'password':password, 'confirm_password':password}
