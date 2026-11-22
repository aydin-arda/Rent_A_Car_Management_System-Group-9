# Rent A Car Management System — CMPE341

A PostgreSQL-backed rental management web application built with Flask. The repository is structured to satisfy the CMPE341 project requirements: relational schema, sample data, meaningful SQL queries, authentication, role-based authorization, CRUD operations and Docker Compose startup.

## Requirements
- Docker Desktop / Docker Engine and Docker Compose
- A web browser

## Run
From the project root:

```bash
docker compose up --build
```

Open **http://localhost:5000**.

To stop:

```bash
docker compose down
```

To remove the database volume and reset the sample database:

```bash
docker compose down -v
```

## Demo accounts
- Administrator: `admin` / `RentCar123!`
- Customer: `customer` / `RentCar123!`
- Secondary administrator (additional seeded account): `admin2` / `RentCar123!`

Passwords are stored as Werkzeug-generated password hashes in `app_users.password_hash`, not as plaintext.

## Roles
- **ADMIN**: view inventory and bookings; insert, update and delete vehicles; create bookings for customers; update booking status.
- **CUSTOMER**: view inventory; create and view their own booking requests.

## Database
PostgreSQL 16. Schema and sample records are initialized from `init.sql` on the first database startup. There are seven entities/tables: `app_users`, `branches`, `customers`, `vehicles`, `bookings`, `payments`, and `maintenance_records`.

## Important deployment notes
This is a local, reproducible course-project setup, not a production-hardened service. Before public deployment:
1. Change `SECRET_KEY` and database credentials.
2. Use HTTPS behind a reverse proxy.
3. Configure persistent backups and restrict database network access.
4. Add server-side validation, CSRF protection, audit logging and rate limiting.
5. Use a production WSGI server such as Gunicorn.

## Suggested GitHub repository
`rent-a-car-management-system-group-<group-number>`

Add all group members as collaborators. The course guideline asks for a public GitHub repository and a README containing access instructions and test credentials. Do not publish real customer data or real passwords.

## Cloud deployment checklist
1. Create a Linux VM with a cloud provider.
2. Install Docker Engine and the Compose plugin.
3. Clone this repository to the VM.
4. Set production secrets in the compose environment.
5. Run `docker compose up -d --build`.
6. Configure the VM firewall and reverse proxy, then verify the public IP over HTTPS.

Cloud provisioning and public deployment require the team's cloud account and credentials and are not performed by this repository.
