"""Regenerate API and data dictionary documentation from running app/schema."""
from pathlib import Path
import requests
from sqlalchemy.dialects import mysql
from .app.db import Base
from .app import models

ROOT = Path(__file__).resolve().parents[1]


def main():
    response=requests.get('http://127.0.0.1:8000/openapi.json',timeout=10);response.raise_for_status()
    schema=response.json()
    lines=['# API reference', '', 'Generated from the running FastAPI OpenAPI schema. Interactive reference: `/docs`.',
           '', 'Browser requests use the HttpOnly `interviewace_session` cookie. Mutating cookie-authenticated requests require `X-Requested-With: InterviewAce` and a matching Origin when supplied. Direct API clients may use Bearer tokens returned when the browser header is absent. WebSockets are documented in PROJECT_GUIDE.md.', '']
    for path,methods in schema['paths'].items():
        for method,operation in methods.items():
            if method not in ('get','post','patch','delete','put'):continue
            lines.extend([f'## {method.upper()} {path}', '', operation.get('summary',''), ''])
            if operation.get('security'):lines.extend(['Authentication required.', ''])
            for param in operation.get('parameters',[]):
                lines.append(f"- `{param['name']}` ({param['in']}): `{param.get('schema',{}).get('type','value')}`; required: {param.get('required',False)}.")
            for media,body in operation.get('requestBody',{}).get('content',{}).items():
                reference=body.get('schema',{}).get('$ref','').rsplit('/',1)[-1]
                lines.append(f'- Body: `{media}`, schema `{reference or body.get("schema",{}).get("type","object")}`.')
            lines.extend(['', 'Responses: '+', '.join(operation.get('responses',{}))+'.', ''])
    lines.extend(['# Request models', '', 'Validation limits are included below. Registration also enforces the shared password, name, contact and confirmation rules described in PROJECT_GUIDE.md.', ''])
    for name,model in schema.get('components',{}).get('schemas',{}).items():
        properties=model.get('properties',{})
        if not properties:continue
        lines.extend([f'## {name}', '', '| Field | Required | Type / limits |','| --- | --- | --- |'])
        for field,definition in properties.items():
            rules={k:v for k,v in definition.items() if k not in ('title','description','default')}
            lines.append(f'| `{field}` | {field in model.get("required",[])} | `{str(rules).replace("|","/")}` |')
        lines.append('')
    (ROOT/'docs/API.md').write_text('\n'.join(lines),encoding='utf-8')
    lines=['# Data dictionary', '', 'Generated from SQLAlchemy metadata. All application data uses MySQL/InnoDB; files remain in private local storage. No actual records or credentials are included.', '']
    for table in Base.metadata.sorted_tables:
        lines.extend([f'## {table.name}', '', '| Column | MySQL type | Nullable | Key / relationship |','| --- | --- | --- | --- |'])
        for column in table.columns:
            keys=[]
            if column.primary_key:keys.append('primary key')
            if column.unique:keys.append('unique')
            if column.index:keys.append('indexed')
            for foreign in column.foreign_keys:keys.append(f'{foreign.target_fullname}; on delete {foreign.ondelete}')
            lines.append(f'| `{column.name}` | `{column.type.compile(dialect=mysql.dialect())}` | {column.nullable} | {"; ".join(keys)} |')
        lines.append('')
    (ROOT/'docs/DATA_DICTIONARY.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Generated docs/API.md and docs/DATA_DICTIONARY.md; no personal data included.')


if __name__=='__main__':main()
