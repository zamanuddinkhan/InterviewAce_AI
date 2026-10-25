# API reference

Generated from the running FastAPI OpenAPI schema. Interactive reference: `/docs`.

Browser requests use the HttpOnly `interviewace_session` cookie. Mutating cookie-authenticated requests require `X-Requested-With: InterviewAce` and a matching Origin when supplied. Direct API clients may use Bearer tokens returned when the browser header is absent. WebSockets are documented in PROJECT_GUIDE.md.

## GET /api/rooms

History

Authentication required.


Responses: 200.

## POST /api/rooms

Create

Authentication required.

- Body: `application/json`, schema `CreateRoom`.

Responses: 201, 422.

## POST /api/rooms/{room_id}/join

Join

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## GET /api/rooms/{room_id}

Details

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/ws-ticket

Issue Ws Ticket

Authentication required. The ticket is one-use, room-scoped and expires after 45 seconds. It is intended for a browser connecting directly to the PC backend's secure WebSocket after requesting the ticket through the same-origin API proxy.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## DELETE /api/rooms/{room_id}

Delete Room

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/start

Start

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/end

End

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/questions

Question

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `application/json`, schema `TextBody`.

Responses: 200, 422.

## POST /api/rooms/{room_id}/problem

Problem

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `application/json`, schema `ProblemBody`.

Responses: 200, 422.

## POST /api/rooms/{room_id}/execute

Execute

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `application/json`, schema `CodeBody`.

Responses: 200, 422.

## POST /api/rooms/{room_id}/documents

Upload

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `multipart/form-data`, schema `Body_upload_api_rooms__room_id__documents_post`.

Responses: 201, 422.

## GET /api/rooms/{room_id}/documents/{document_id}

Download

Authentication required.

- `room_id` (path): `string`; required: True.
- `document_id` (path): `integer`; required: True.

Responses: 200, 422.

## DELETE /api/rooms/{room_id}/documents/{document_id}

Delete Document

Authentication required.

- `room_id` (path): `string`; required: True.
- `document_id` (path): `integer`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/rag

Generate

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `application/json`, schema `GenerateBody`.

Responses: 200, 422.

## POST /api/rooms/{room_id}/communication

Audio

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `multipart/form-data`, schema `Body_audio_api_rooms__room_id__communication_post`.

Responses: 200, 422.

## POST /api/rooms/{room_id}/feedback

Feedback

Authentication required.

- `room_id` (path): `string`; required: True.
- Body: `application/json`, schema `FeedbackBody`.

Responses: 200, 422.

## GET /api/rooms/{room_id}/report

Report

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## POST /api/rooms/{room_id}/undo-delete

Undo Delete

Authentication required.

- `room_id` (path): `string`; required: True.

Responses: 200, 422.

## GET /

Home


Responses: 200.

## GET /api/health

Health


Responses: 200.

## GET /api/live

Live


Responses: 200.

## GET /api/monitoring

Monitoring

Authentication required.


Responses: 200.

## POST /api/register

Register

- Body: `application/json`, schema `RegisterBody`.

Responses: 201, 422.

## POST /api/login

Login

- Body: `application/json`, schema `LoginBody`.

Responses: 200, 422.

## GET /api/me

Me

Authentication required.


Responses: 200.

## DELETE /api/me

Delete Account

Authentication required.


Responses: 200.

## PATCH /api/me

Update Profile

Authentication required.

- Body: `application/json`, schema `ProfileBody`.

Responses: 200, 422.

## POST /api/logout

Logout

Authentication required.


Responses: 200.

## GET /api/sessions

Sessions

Authentication required.


Responses: 200.

## DELETE /api/sessions

End Sessions

Authentication required.


Responses: 200.

## POST /api/change-password

Change Password

Authentication required.

- Body: `application/json`, schema `ChangePasswordBody`.

Responses: 200, 422.

## POST /api/password-reset

Reset Password

- Body: `application/json`, schema `ResetBody`.

Responses: 200, 422.

## POST /api/recovery-code

Recovery Code

Authentication required.

- Body: `application/json`, schema `RecoveryBody`.

Responses: 200, 422.

## GET /api/resumes

List Resumes

Authentication required.


Responses: 200.

## POST /api/resumes

Upload Resume

Authentication required.

- Body: `multipart/form-data`, schema `Body_upload_resume_api_resumes_post`.

Responses: 201, 422.

## DELETE /api/resumes/{resume_id}

Delete Resume

Authentication required.

- `resume_id` (path): `integer`; required: True.

Responses: 200, 422.

## POST /api/interviews/start

Start Interview

Authentication required.

- Body: `application/json`, schema `StartBody`.

Responses: 201, 422.

## GET /api/interviews

List Interviews

Authentication required.


Responses: 200.

## GET /api/interviews/{interview_id}

Interview Details

Authentication required.

- `interview_id` (path): `integer`; required: True.

Responses: 200, 422.

## DELETE /api/interviews/{interview_id}

Delete Interview

Authentication required.

- `interview_id` (path): `integer`; required: True.

Responses: 200, 422.

## POST /api/interviews/{interview_id}/transcribe

Transcribe Answer

Authentication required.

- `interview_id` (path): `integer`; required: True.
- Body: `multipart/form-data`, schema `Body_transcribe_answer_api_interviews__interview_id__transcribe_post`.

Responses: 200, 422.

## POST /api/interviews/{interview_id}/answer

Submit Answer

Authentication required.

- `interview_id` (path): `integer`; required: True.
- Body: `application/json`, schema `AnswerBody`.

Responses: 200, 422.

## GET /api/interviews/{interview_id}/report

Report

Authentication required.

- `interview_id` (path): `integer`; required: True.

Responses: 200, 422.

# Request models

Validation limits are included below. Registration also enforces the shared password, name, contact and confirmation rules described in PROJECT_GUIDE.md.

## AnswerBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `text` | True | `{'type': 'string', 'maxLength': 5000, 'minLength': 2}` |

## Body_audio_api_rooms__room_id__communication_post

| Field | Required | Type / limits |
| --- | --- | --- |
| `consent` | True | `{'type': 'boolean'}` |
| `file` | True | `{'type': 'string', 'contentMediaType': 'application/octet-stream'}` |

## Body_transcribe_answer_api_interviews__interview_id__transcribe_post

| Field | Required | Type / limits |
| --- | --- | --- |
| `consent` | True | `{'type': 'boolean'}` |
| `file` | True | `{'type': 'string', 'contentMediaType': 'application/octet-stream'}` |

## Body_upload_api_rooms__room_id__documents_post

| Field | Required | Type / limits |
| --- | --- | --- |
| `file` | True | `{'type': 'string', 'contentMediaType': 'application/octet-stream'}` |
| `kind` | False | `{'type': 'string'}` |
| `note` | False | `{'type': 'string', 'maxLength': 5000}` |

## Body_upload_resume_api_resumes_post

| Field | Required | Type / limits |
| --- | --- | --- |
| `file` | True | `{'type': 'string', 'contentMediaType': 'application/octet-stream'}` |

## ChangePasswordBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `current_password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 1}` |
| `new_password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 12}` |
| `confirm_password` | True | `{'type': 'string', 'maxLength': 128}` |

## CodeBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `source` | True | `{'type': 'string', 'maxLength': 20000, 'minLength': 1}` |
| `final` | False | `{'type': 'boolean'}` |

## CreateRoom

| Field | Required | Type / limits |
| --- | --- | --- |
| `topic` | True | `{'type': 'string', 'maxLength': 100, 'minLength': 3}` |
| `duration_seconds` | False | `{'type': 'integer', 'maximum': 14400.0, 'minimum': 60.0}` (1–240 minutes) |

## FeedbackBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `technical` | True | `{'type': 'number', 'maximum': 100.0, 'minimum': 0.0}` |
| `problem_solving` | True | `{'type': 'number', 'maximum': 100.0, 'minimum': 0.0}` |
| `communication` | True | `{'type': 'number', 'maximum': 100.0, 'minimum': 0.0}` |
| `strengths` | True | `{'type': 'string', 'maxLength': 3000, 'minLength': 2}` |
| `improvements` | True | `{'type': 'string', 'maxLength': 3000, 'minLength': 2}` |

## GenerateBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `document_id` | True | `{'type': 'integer'}` |
| `query` | True | `{'type': 'string', 'maxLength': 300, 'minLength': 2}` |

## HTTPValidationError

| Field | Required | Type / limits |
| --- | --- | --- |
| `detail` | False | `{'items': {'$ref': '#/components/schemas/ValidationError'}, 'type': 'array'}` |

## LoginBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `email` | True | `{'type': 'string', 'format': 'email'}` |
| `password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 1}` |

## ProblemBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `title` | True | `{'type': 'string', 'maxLength': 200, 'minLength': 2}` |
| `statement` | True | `{'type': 'string', 'maxLength': 10000, 'minLength': 5}` |
| `constraints` | False | `{'type': 'string', 'maxLength': 2000}` |
| `starter` | False | `{'type': 'string', 'maxLength': 10000}` |
| `tests` | True | `{'items': {'$ref': '#/components/schemas/TestCase'}, 'type': 'array', 'maxItems': 5, 'minItems': 1}` |

## ProfileBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `first_name` | True | `{'type': 'string', 'maxLength': 50, 'minLength': 1}` |
| `last_name` | True | `{'type': 'string', 'maxLength': 50, 'minLength': 1}` |
| `contact_number` | True | `{'type': 'string', 'maxLength': 32, 'minLength': 8}` |

## RecoveryBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 8}` |

## RegisterBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `first_name` | True | `{'type': 'string', 'maxLength': 50, 'minLength': 1}` |
| `last_name` | True | `{'type': 'string', 'maxLength': 50, 'minLength': 1}` |
| `contact_number` | True | `{'type': 'string', 'maxLength': 32, 'minLength': 8}` |
| `email` | True | `{'type': 'string', 'format': 'email'}` |
| `password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 12}` |
| `confirm_password` | True | `{'type': 'string', 'maxLength': 128}` |

## ResetBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `email` | True | `{'type': 'string', 'format': 'email'}` |
| `recovery_code` | True | `{'type': 'string', 'maxLength': 200, 'minLength': 10}` |
| `new_password` | True | `{'type': 'string', 'maxLength': 128, 'minLength': 12}` |
| `confirm_password` | True | `{'type': 'string', 'maxLength': 128}` |

## StartBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `role` | True | `{'type': 'string', 'maxLength': 100, 'minLength': 3}` |
| `kind` | False | `{'type': 'string', 'pattern': '^(technical/hr/mixed/custom)$'}` |
| `custom_kind` | False | `{'anyOf': [{'type': 'string', 'maxLength': 100}, {'type': 'null'}]}` |
| `difficulty` | False | `{'type': 'string', 'pattern': '^(easy/medium/hard)$'}` |
| `question_limit` | False | `{'type': 'integer', 'maximum': 50.0, 'minimum': 1.0}` |
| `resume_id` | False | `{'anyOf': [{'type': 'integer'}, {'type': 'null'}]}` |

## TestCase

| Field | Required | Type / limits |
| --- | --- | --- |
| `input` | False | `{'type': 'string', 'maxLength': 5000}` |
| `expected` | True | `{'type': 'string', 'maxLength': 5000}` |

## TextBody

| Field | Required | Type / limits |
| --- | --- | --- |
| `text` | True | `{'type': 'string', 'maxLength': 5000, 'minLength': 2}` |

## ValidationError

| Field | Required | Type / limits |
| --- | --- | --- |
| `loc` | True | `{'items': {'anyOf': [{'type': 'string'}, {'type': 'integer'}]}, 'type': 'array'}` |
| `msg` | True | `{'type': 'string'}` |
| `type` | True | `{'type': 'string'}` |
| `input` | False | `{}` |
| `ctx` | False | `{'type': 'object'}` |
