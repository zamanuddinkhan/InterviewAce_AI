# MySQL on this PC

The project now uses your **existing MySQL Community Server on this PC at port 3306**, with the connection in `.env`.

For a public Vercel + PC-backend deployment, the current local root account is not appropriate for the public-facing application. In Workbench, create a separate TCP user for `127.0.0.1` and grant only the schema-level permissions the app needs:

```sql
CREATE USER 'interviewace_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON interviewace.* TO 'interviewace_app'@'127.0.0.1';
```

Then update only `DATABASE_URL` in the private `.env` to `mysql+pymysql://interviewace_app:URL_ENCODED_PASSWORD@127.0.0.1:3306/interviewace`. URL-encode reserved password characters. Take a verified backup first and test the app with the new user before enabling the tunnel. Keep MySQL listening on localhost; Vercel accesses it only through the FastAPI application. The deployment user has schema migration rights but cannot create/drop other databases; the isolated MySQL verification suite still requires a separate test account with create/drop rights.

| Setting | Configured value |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `3306` |
| Database/default schema | `interviewace` |
| Configured user | `root` (your current local configuration) |
| Password | Saved privately in `.env`; never included in documentation |
| Persistence | Existing PC MySQL80 server's database storage |
| API | `http://127.0.0.1:8000` |

The earlier managed project instance on port 3307 and its `data/mysql` files are retained but are no longer the active application connection. `LOCAL_MYSQL=0` prevents the launch helper from managing that instance for this app. Existing unrelated databases are preserved.

## Open the project database in MySQL Workbench

1. Ensure the MySQL80 Windows service is running, then start the project with `run.cmd` (CMD) or `./run.ps1` (PowerShell).
2. In MySQL Workbench, add a connection named **InterviewAce Local** using **Standard TCP/IP**.
3. Set hostname to **127.0.0.1**, port to **3306**, username to **root** and default schema to **interviewace**.
4. Use your existing PC MySQL root password. Workbench needs the original password, not the percent-encoded URL representation in `DATABASE_URL`. Save it only in your private Workbench vault if desired; do not paste it into chat or source files.
5. Click **Test Connection**, open the connection and refresh **Schemas**.
6. Inspect the connection and tables with:

```sql
SELECT DATABASE(), VERSION();
SHOW TABLES;
SELECT id, first_name, last_name, created_at FROM users;
```

The app connection string is already saved as `DATABASE_URL` in `.env`. It points to the host/port/schema above. Keep the configured `.env`; replacing it with `.env.example` would overwrite the generated private connection settings.

## Verify and preserve the connection

- Open `/api/health`: it performs a real SQL query and should return `status: ok`, `database: mysql`.
- Run `.venv/Scripts/python.exe -B -m backend.verify_mysql` for the isolated real-MySQL suite. It creates/removes a separate `interviewace_test_` database using the configured connection; the account needs create/drop-database privileges. It never treats application records as test fixtures.
- Use SQL/file backups for portable recovery and protect `.env` separately. The existing `data/mysql` directory belongs to the previous optional 3307 instance; do not delete it merely because the current app uses 3306.

The switch to 3306 is complete and was verified with real queries and isolated API tests. Root is convenient for your local development setup; use a restricted application account before a public deployment. No root password reset or raw data-directory replacement was performed. Records from the former 3307 instance are not automatically merged into 3306.
