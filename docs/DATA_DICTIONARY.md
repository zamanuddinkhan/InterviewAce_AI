# Data dictionary

Generated from SQLAlchemy metadata. All application data uses MySQL/InnoDB; files remain in private local storage. No actual records or credentials are included.

## revoked_tokens

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `digest` | `VARCHAR(64)` | False | primary key |
| `expires_at` | `DOUBLE` | False |  |

## users

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `name` | `VARCHAR(100)` | False |  |
| `first_name` | `VARCHAR(50)` | False |  |
| `last_name` | `VARCHAR(50)` | False |  |
| `contact_number` | `VARCHAR(16)` | False |  |
| `email` | `VARCHAR(255)` | False | unique; indexed |
| `password_hash` | `VARCHAR(255)` | False |  |
| `created_at` | `DATETIME` | False |  |

## login_sessions

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `digest` | `VARCHAR(64)` | False | primary key |
| `user_id` | `INTEGER` | False | indexed; users.id; on delete CASCADE |
| `created_at` | `DOUBLE` | False |  |
| `last_seen_at` | `DOUBLE` | False |  |
| `expires_at` | `DOUBLE` | False | indexed |

## peer_rooms

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `VARCHAR(32)` | False | primary key |
| `interviewer_id` | `INTEGER` | False | indexed; users.id; on delete CASCADE |
| `candidate_id` | `INTEGER` | True | users.id; on delete SET NULL |
| `topic` | `VARCHAR(100)` | False |  |
| `duration_seconds` | `INTEGER` | False |  |
| `status` | `VARCHAR(20)` | False |  |
| `started_at` | `DOUBLE` | True |  |
| `ended_at` | `DOUBLE` | True |  |
| `code` | `TEXT` | False |  |
| `problem` | `JSON` | True |  |
| `created_at` | `DATETIME` | False |  |

## recovery_codes

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `user_id` | `INTEGER` | False | primary key; users.id; on delete CASCADE |
| `code_hash` | `VARCHAR(255)` | False |  |

## resumes

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `user_id` | `INTEGER` | False | indexed; users.id; on delete CASCADE |
| `filename` | `VARCHAR(255)` | False |  |
| `stored_path` | `VARCHAR(600)` | False |  |
| `extracted_text` | `TEXT` | False |  |
| `created_at` | `DATETIME` | False |  |

## token_versions

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `user_id` | `INTEGER` | False | primary key; users.id; on delete CASCADE |
| `version` | `INTEGER` | False |  |

## documents

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `room_id` | `VARCHAR(32)` | False | indexed; peer_rooms.id; on delete CASCADE |
| `owner_id` | `INTEGER` | False | users.id; on delete CASCADE |
| `filename` | `VARCHAR(255)` | False |  |
| `stored_path` | `VARCHAR(600)` | False |  |
| `kind` | `VARCHAR(20)` | False |  |
| `pages` | `JSON` | False |  |
| `analysis` | `JSON` | True |  |

## interviews

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `user_id` | `INTEGER` | False | indexed; users.id; on delete CASCADE |
| `resume_id` | `INTEGER` | True | resumes.id; on delete SET NULL |
| `role` | `VARCHAR(100)` | False |  |
| `kind` | `VARCHAR(20)` | False |  |
| `custom_kind` | `VARCHAR(100)` | True |  |
| `difficulty` | `VARCHAR(20)` | False |  |
| `question_limit` | `INTEGER` | False |  |
| `status` | `VARCHAR(20)` | False |  |
| `created_at` | `DATETIME` | False |  |

## room_events

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `room_id` | `VARCHAR(32)` | False | indexed; peer_rooms.id; on delete CASCADE |
| `user_id` | `INTEGER` | False | users.id; on delete CASCADE |
| `kind` | `VARCHAR(30)` | False |  |
| `payload` | `JSON` | False |  |
| `created_at` | `DATETIME` | False |  |

## questions

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `interview_id` | `INTEGER` | False | indexed; interviews.id; on delete CASCADE |
| `position` | `INTEGER` | False |  |
| `text` | `TEXT` | False |  |
| `difficulty` | `VARCHAR(20)` | False |  |

## answers

| Column | MySQL type | Nullable | Key / relationship |
| --- | --- | --- | --- |
| `id` | `INTEGER` | False | primary key |
| `question_id` | `INTEGER` | False | unique; questions.id; on delete CASCADE |
| `text` | `TEXT` | False |  |
| `correctness` | `FLOAT` | False |  |
| `relevance` | `FLOAT` | False |  |
| `clarity` | `FLOAT` | False |  |
| `examples` | `FLOAT` | False |  |
| `overall` | `FLOAT` | False |  |
| `feedback` | `TEXT` | False |  |
| `improved_answer` | `TEXT` | False |  |
| `created_at` | `DATETIME` | False |  |
