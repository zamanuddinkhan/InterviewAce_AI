"""Shared validation rules for registration, profile and password recovery."""
import re
import unicodedata
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, model_validator


def person_name(value: str) -> str:
    value = ' '.join(unicodedata.normalize('NFC', value).split())
    if not value or not any(c.isalpha() for c in value) or any(not (c.isalpha() or c in " '-.") for c in value):
        raise ValueError('Use letters, spaces, apostrophes, periods or hyphens for names.')
    return value


def contact(value: str) -> str:
    value = re.sub(r'[\s()\-]', '', value)
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', value):
        raise ValueError('Enter a contact number with country code, for example +91 98765 43210 (8–15 digits).')
    return value


def strong_password(value: str) -> str:
    if not (any(c.islower() for c in value) and any(c.isupper() for c in value)
            and any(c.isdigit() for c in value) and any(not c.isalnum() and not c.isspace() for c in value)):
        raise ValueError('Use 12–128 characters with uppercase, lowercase, a number and a symbol.')
    if value != value.strip() or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Do not use control characters or leading/trailing spaces in passwords.')
    if any(common in value.lower() for common in ('password', 'qwerty', 'letmein', 'interviewace')):
        raise ValueError('Avoid common passwords and the application name. Choose a unique passphrase.')
    return value


Name = Annotated[str, Field(min_length=1, max_length=50), AfterValidator(person_name)]
Contact = Annotated[str, Field(min_length=8, max_length=32), AfterValidator(contact)]
StrongPassword = Annotated[str, Field(min_length=12, max_length=128), AfterValidator(strong_password)]


class RegisterBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    first_name: Name
    last_name: Name
    contact_number: Contact
    email: EmailStr
    password: StrongPassword
    confirm_password: str = Field(max_length=128)

    @model_validator(mode='after')
    def matching(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match.')
        if len(self.first_name + ' ' + self.last_name) > 100:
            raise ValueError('Combined name must be at most 100 characters.')
        if self.email.split('@')[0].lower() in self.password.lower() and len(self.email.split('@')[0]) >= 4:
            raise ValueError('Do not include your email address in your password.')
        return self


class ProfileBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    first_name: Name
    last_name: Name
    contact_number: Contact


class ResetBody(BaseModel):
    email: EmailStr
    recovery_code: str = Field(min_length=10, max_length=200)
    new_password: StrongPassword
    confirm_password: str = Field(max_length=128)

    @model_validator(mode='after')
    def matching(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match.')
        return self


class ChangePasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: StrongPassword
    confirm_password: str = Field(max_length=128)

    @model_validator(mode='after')
    def matching(self):
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match.')
        if self.new_password == self.current_password:
            raise ValueError('Choose a different password.')
        return self
