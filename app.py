import os
from datetime import date
from functools import wraps
import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-in-production")
DB_URL = os.getenv("DATABASE_URL", "postgresql://rentcar:rentcar@db:5432/rentcar")

def db():
    return psycopg.connect(DB_URL, row_factory=dict_row)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if session.get("role") != role:
                flash("You are not authorized to access that operation.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def ensure_demo_users():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM app_users")
            if cur.fetchone()["n"] == 0:
                cur.execute("INSERT INTO app_users(username,password_hash,role) VALUES (%s,%s,'ADMIN'),(%s,%s,'CUSTOMER')",
                    ("admin", generate_password_hash("RentCar123!"),
                     "customer", generate_password_hash("RentCar123!")))
                cur.execute("INSERT INTO app_users(username,password_hash,role) VALUES (%s,%s,'ADMIN')",
                    ("admin2", generate_password_hash("RentCar123!")))
                cur.execute("""INSERT INTO customers(user_id,first_name,last_name,email,phone,driver_license_no,license_expiry)
                    SELECT user_id,'Demo','Customer','demo.customer@example.com','0500-000-0000','DEMO-LICENSE-01','2030-12-31'
                    FROM app_users WHERE username='customer'""")

@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM app_users WHERE username=%s AND is_active=TRUE", (username,))
                user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.update(user_id=user["user_id"], username=user["username"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM vehicles WHERE status='AVAILABLE'")
            available = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM bookings")
            bookings = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM customers")
            customers = cur.fetchone()["n"]
    return render_template("dashboard.html", available=available, bookings=bookings, customers=customers)

@app.route("/vehicles")
@login_required
def vehicles():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT v.*, b.branch_name FROM vehicles v JOIN branches b ON b.branch_id=v.branch_id
                           ORDER BY v.vehicle_id""")
            rows = cur.fetchall()
            cur.execute("SELECT branch_id,branch_name FROM branches ORDER BY branch_name")
            branches = cur.fetchall()
    return render_template("vehicles.html", vehicles=rows, branches=branches)

@app.route("/vehicles/add", methods=["POST"])
@role_required("ADMIN")
def add_vehicle():
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO vehicles(branch_id,plate_no,brand,model,model_year,category,transmission,daily_rate,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (request.form["branch_id"],request.form["plate_no"].strip(),request.form["brand"].strip(),
                     request.form["model"].strip(),request.form["model_year"],request.form["category"],
                     request.form["transmission"],request.form["daily_rate"],request.form["status"]))
        flash("Vehicle added.", "success")
    except Exception as e:
        flash(f"Could not add vehicle: {e}", "error")
    return redirect(url_for("vehicles"))

@app.route("/vehicles/<int:vehicle_id>/update", methods=["POST"])
@role_required("ADMIN")
def update_vehicle(vehicle_id):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE vehicles SET branch_id=%s, daily_rate=%s, status=%s WHERE vehicle_id=%s""",
                    (request.form["branch_id"],request.form["daily_rate"],request.form["status"],vehicle_id))
        flash("Vehicle updated.", "success")
    except Exception as e:
        flash(f"Could not update vehicle: {e}", "error")
    return redirect(url_for("vehicles"))

@app.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@role_required("ADMIN")
def delete_vehicle(vehicle_id):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM vehicles WHERE vehicle_id=%s", (vehicle_id,))
        flash("Vehicle deleted.", "success")
    except Exception as e:
        flash(f"Vehicle cannot be deleted because it may be referenced by a booking: {e}", "error")
    return redirect(url_for("vehicles"))

@app.route("/bookings")
@login_required
def bookings():
    with db() as conn:
        with conn.cursor() as cur:
            base = """SELECT bk.booking_id, c.first_name || ' ' || c.last_name AS customer,
                      v.brand || ' ' || v.model AS vehicle, bk.pickup_date, bk.return_date,
                      bk.booking_status, bk.total_amount
                      FROM bookings bk JOIN customers c ON c.customer_id=bk.customer_id
                      JOIN vehicles v ON v.vehicle_id=bk.vehicle_id"""
            if session["role"] == "ADMIN":
                cur.execute(base + " ORDER BY bk.booking_id DESC")
            else:
                cur.execute(base + """ JOIN app_users au ON au.user_id=c.user_id
                            WHERE au.user_id=%s ORDER BY bk.booking_id DESC""", (session["user_id"],))
            rows = cur.fetchall()
            cur.execute("SELECT customer_id,first_name,last_name FROM customers ORDER BY customer_id")
            customer_rows = cur.fetchall()
            cur.execute("SELECT vehicle_id,brand,model,daily_rate FROM vehicles WHERE status='AVAILABLE' ORDER BY brand")
            vehicle_rows = cur.fetchall()
            cur.execute("SELECT branch_id,branch_name FROM branches ORDER BY branch_id")
            branch_rows = cur.fetchall()
    return render_template("bookings.html", bookings=rows, customers=customer_rows, vehicles=vehicle_rows, branches=branch_rows)

@app.route("/bookings/add", methods=["POST"])
@login_required
def add_booking():
    try:
        customer_id = request.form.get("customer_id")
        if session["role"] == "CUSTOMER":
            with db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT customer_id FROM customers WHERE user_id=%s", (session["user_id"],))
                    own = cur.fetchone()
            if not own:
                raise ValueError("Customer profile is missing.")
            customer_id = own["customer_id"]
        start = date.fromisoformat(request.form["pickup_date"])
        end = date.fromisoformat(request.form["return_date"])
        if end <= start:
            raise ValueError("Return date must be later than pickup date.")
        days = (end-start).days
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT daily_rate FROM vehicles WHERE vehicle_id=%s AND status='AVAILABLE'", (request.form["vehicle_id"],))
                v = cur.fetchone()
                if not v:
                    raise ValueError("Selected vehicle is not available.")
                total = days * float(v["daily_rate"])
                cur.execute("""INSERT INTO bookings(customer_id,vehicle_id,pickup_branch_id,return_branch_id,pickup_date,return_date,booking_status,total_amount)
                    VALUES (%s,%s,%s,%s,%s,%s,'PENDING',%s)""",
                    (customer_id,request.form["vehicle_id"],request.form["pickup_branch_id"],request.form["return_branch_id"],start,end,total))
        flash("Booking request created.", "success")
    except Exception as e:
        flash(f"Could not create booking: {e}", "error")
    return redirect(url_for("bookings"))

@app.route("/bookings/<int:booking_id>/status", methods=["POST"])
@role_required("ADMIN")
def update_booking_status(booking_id):
    status = request.form["booking_status"]
    if status not in ("PENDING","CONFIRMED","COMPLETED","CANCELLED"):
        flash("Invalid booking status.", "error")
    else:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE bookings SET booking_status=%s WHERE booking_id=%s",(status,booking_id))
        flash("Booking status updated.", "success")
    return redirect(url_for("bookings"))


@app.route("/customers")
@role_required("ADMIN")
def customers():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT customer_id, first_name, last_name, email, phone,
                                 driver_license_no, license_expiry, created_at
                          FROM customers ORDER BY customer_id""")
            rows = cur.fetchall()
    return render_template("customers.html", customers=rows)

@app.route("/customers/add", methods=["POST"])
@role_required("ADMIN")
def add_customer():
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO customers
                    (first_name, last_name, email, phone, driver_license_no, license_expiry)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (request.form["first_name"].strip(), request.form["last_name"].strip(),
                     request.form["email"].strip().lower(), request.form["phone"].strip(),
                     request.form["driver_license_no"].strip(),
                     date.fromisoformat(request.form["license_expiry"])))
        flash("Customer added successfully.", "success")
    except Exception as e:
        flash(f"Could not add customer. Check required fields and unique email, phone, and license number. ({e})", "error")
    return redirect(url_for("customers"))

@app.route("/customers/<int:customer_id>/update", methods=["POST"])
@role_required("ADMIN")
def update_customer(customer_id):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE customers SET first_name=%s, last_name=%s, email=%s,
                    phone=%s, driver_license_no=%s, license_expiry=%s
                    WHERE customer_id=%s""",
                    (request.form["first_name"].strip(), request.form["last_name"].strip(),
                     request.form["email"].strip().lower(), request.form["phone"].strip(),
                     request.form["driver_license_no"].strip(),
                     date.fromisoformat(request.form["license_expiry"]), customer_id))
                if cur.rowcount == 0:
                    raise ValueError("Customer not found.")
        flash("Customer updated successfully.", "success")
    except Exception as e:
        flash(f"Could not update customer. Check required fields and unique email, phone, and license number. ({e})", "error")
    return redirect(url_for("customers"))

@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
@role_required("ADMIN")
def delete_customer(customer_id):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM customers WHERE customer_id=%s", (customer_id,))
                if cur.rowcount == 0:
                    raise ValueError("Customer not found.")
        flash("Customer deleted successfully.", "success")
    except Exception:
        flash("Customer cannot be deleted because the customer may have existing bookings.", "error")
    return redirect(url_for("customers"))



@app.route("/payments")
@role_required("ADMIN")
def payments():
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT p.payment_id, p.booking_id, p.payment_date, p.amount,
                                  p.payment_method, p.payment_status,
                                  c.first_name || ' ' || c.last_name AS customer,
                                  v.brand || ' ' || v.model AS vehicle
                           FROM payments p
                           JOIN bookings bk ON bk.booking_id=p.booking_id
                           JOIN customers c ON c.customer_id=bk.customer_id
                           JOIN vehicles v ON v.vehicle_id=bk.vehicle_id
                           ORDER BY p.payment_id DESC""")
            rows = cur.fetchall()
            cur.execute("""SELECT bk.booking_id, c.first_name || ' ' || c.last_name AS customer,
                                  v.brand || ' ' || v.model AS vehicle, bk.total_amount
                           FROM bookings bk
                           JOIN customers c ON c.customer_id=bk.customer_id
                           JOIN vehicles v ON v.vehicle_id=bk.vehicle_id
                           LEFT JOIN payments p ON p.booking_id=bk.booking_id
                           WHERE p.payment_id IS NULL
                           ORDER BY bk.booking_id""")
            available_bookings = cur.fetchall()
    return render_template("payments.html", payments=rows, bookings=available_bookings)

@app.route("/payments/add", methods=["POST"])
@role_required("ADMIN")
def add_payment():
    try:
        amount = float(request.form["amount"])
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        method = request.form["payment_method"]
        status = request.form["payment_status"]
        if method not in ("CARD", "CASH", "BANK_TRANSFER"):
            raise ValueError("Invalid payment method.")
        if status not in ("PAID", "PENDING", "REFUNDED"):
            raise ValueError("Invalid payment status.")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO payments
                    (booking_id, payment_date, amount, payment_method, payment_status)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (request.form["booking_id"], date.fromisoformat(request.form["payment_date"]),
                     amount, method, status))
        flash("Payment added successfully.", "success")
    except Exception as e:
        flash(f"Could not add payment. Check the booking and payment details. ({e})", "error")
    return redirect(url_for("payments"))

@app.route("/payments/<int:payment_id>/update", methods=["POST"])
@role_required("ADMIN")
def update_payment(payment_id):
    try:
        amount = float(request.form["amount"])
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        method = request.form["payment_method"]
        status = request.form["payment_status"]
        if method not in ("CARD", "CASH", "BANK_TRANSFER"):
            raise ValueError("Invalid payment method.")
        if status not in ("PAID", "PENDING", "REFUNDED"):
            raise ValueError("Invalid payment status.")
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""UPDATE payments SET payment_date=%s, amount=%s,
                               payment_method=%s, payment_status=%s
                               WHERE payment_id=%s""",
                    (date.fromisoformat(request.form["payment_date"]), amount,
                     method, status, payment_id))
                if cur.rowcount == 0:
                    raise ValueError("Payment not found.")
        flash("Payment updated successfully.", "success")
    except Exception as e:
        flash(f"Could not update payment. Check the payment details. ({e})", "error")
    return redirect(url_for("payments"))

@app.route("/payments/<int:payment_id>/delete", methods=["POST"])
@role_required("ADMIN")
def delete_payment(payment_id):
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM payments WHERE payment_id=%s", (payment_id,))
                if cur.rowcount == 0:
                    raise ValueError("Payment not found.")
        flash("Payment deleted successfully.", "success")
    except Exception as e:
        flash(f"Could not delete payment: {e}", "error")
    return redirect(url_for("payments"))


@app.route("/health")
def health():
    return {"status":"ok"}

if __name__ == "__main__":
    import time
    for attempt in range(30):
        try:
            with db() as conn:
                conn.execute("SELECT 1")
            ensure_demo_users()
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
    app.run(host="0.0.0.0", port=5000)
