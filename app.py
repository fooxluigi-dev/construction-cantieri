#!/usr/bin/env python3
"""
ConstructionCo Micro SaaS - Flask API Server
"""
import sqlite3, os, json
from flask import Flask, request, jsonify, g
from datetime import datetime, date

# Vercel-compatible: DB lives next to app.py in deployment directory
import os
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'construction.db')

app = Flask(__name__, static_folder='static', static_url_path='')

# ─── Database helpers ────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    g.pop('db', None)

def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        with open('/tmp/construction-saas/schema.sql') as f:
            conn.executescript(f.read())
        conn.close()
        print(f"[Init] Database created at {DATABASE}")

# ─── JSON helpers ─────────────────────────────────────────────────────────────

def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

def rows_to_list(rows):
    return [row_to_dict(r) for r in rows]

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('index.html')

# ── Jobs ─────────────────────────────────────────────────────────────────────

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    db = get_db()
    rows = db.execute("""
        SELECT j.*, c.name as client_name
        FROM jobs j
        LEFT JOIN clients c ON j.client_id = c.id
        ORDER BY j.created_at DESC
    """).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO jobs (client_id, name, description, status, start_date, end_date, total_value)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('client_id'), data.get('name'), data.get('description'),
        data.get('status', 'active'), data.get('start_date'),
        data.get('end_date'), data.get('total_value', 0)
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM jobs WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE jobs SET client_id=?, name=?, description=?, status=?, start_date=?, end_date=?, total_value=?
        WHERE id=?
    """, (
        data.get('client_id'), data.get('name'), data.get('description'),
        data.get('status'), data.get('start_date'), data.get('end_date'),
        data.get('total_value', 0), job_id
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()))

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    db = get_db()
    db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Clients ───────────────────────────────────────────────────────────────────

@app.route('/api/clients', methods=['GET'])
def get_clients():
    db = get_db()
    rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/clients', methods=['POST'])
def create_client():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO clients (name, phone, email, address)
        VALUES (?, ?, ?, ?)
    """, (data['name'], data.get('phone'), data.get('email'), data.get('address')))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM clients WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE clients SET name=?, phone=?, email=?, address=? WHERE id=?
    """, (data['name'], data.get('phone'), data.get('email'), data.get('address'), client_id))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()))

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    db = get_db()
    db.execute("DELETE FROM clients WHERE id=?", (client_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Punch Items ───────────────────────────────────────────────────────────────

@app.route('/api/jobs/<int:job_id>/punch-items', methods=['GET'])
def get_punch_items(job_id):
    db = get_db()
    rows = db.execute("SELECT * FROM punch_items WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/punch-items', methods=['POST'])
def create_punch_item():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO punch_items (job_id, description, done) VALUES (?, ?, ?)
    """, (data['job_id'], data['description'], data.get('done', 0)))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM punch_items WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/punch-items/<int:item_id>', methods=['PUT'])
def update_punch_item(item_id):
    data = request.json
    db = get_db()
    db.execute("UPDATE punch_items SET description=?, done=? WHERE id=?", 
               (data['description'], data.get('done', 0), item_id))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM punch_items WHERE id=?", (item_id,)).fetchone()))

@app.route('/api/punch-items/<int:item_id>', methods=['DELETE'])
def delete_punch_item(item_id):
    db = get_db()
    db.execute("DELETE FROM punch_items WHERE id=?", (item_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Materials ─────────────────────────────────────────────────────────────────

@app.route('/api/materials', methods=['GET'])
def get_materials():
    db = get_db()
    rows = db.execute("""
        SELECT m.*, j.name as job_name
        FROM materials m
        LEFT JOIN jobs j ON m.job_id = j.id
        ORDER BY m.created_at DESC
    """).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/materials', methods=['POST'])
def create_material():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO materials (job_id, name, quantity, unit, supplier, estimated_cost, ordered, received)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('job_id'), data['name'], data.get('quantity', 1),
        data.get('unit', 'pz'), data.get('supplier'), data.get('estimated_cost', 0),
        data.get('ordered', 0), data.get('received', 0)
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM materials WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/materials/<int:mat_id>', methods=['PUT'])
def update_material(mat_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE materials SET job_id=?, name=?, quantity=?, unit=?, supplier=?, estimated_cost=?, ordered=?, received=?
        WHERE id=?
    """, (
        data.get('job_id'), data['name'], data.get('quantity', 1),
        data.get('unit', 'pz'), data.get('supplier'), data.get('estimated_cost', 0),
        data.get('ordered', 0), data.get('received', 0), mat_id
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM materials WHERE id=?", (mat_id,)).fetchone()))

@app.route('/api/materials/<int:mat_id>', methods=['DELETE'])
def delete_material(mat_id):
    db = get_db()
    db.execute("DELETE FROM materials WHERE id=?", (mat_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Invoices ──────────────────────────────────────────────────────────────────

@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    db = get_db()
    rows = db.execute("""
        SELECT i.*, c.name as client_name, j.name as job_name
        FROM invoices i
        LEFT JOIN clients c ON i.client_id = c.id
        LEFT JOIN jobs j ON i.job_id = j.id
        ORDER BY i.issued_date DESC
    """).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO invoices (job_id, client_id, invoice_number, amount, issued_date, due_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('job_id'), data.get('client_id'), data.get('invoice_number'),
        data['amount'], data.get('issued_date'), data.get('due_date'),
        data.get('status', 'pending'), data.get('notes')
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM invoices WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/invoices/<int:inv_id>', methods=['PUT'])
def update_invoice(inv_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE invoices SET job_id=?, client_id=?, invoice_number=?, amount=?, issued_date=?, due_date=?, status=?, notes=?
        WHERE id=?
    """, (
        data.get('job_id'), data.get('client_id'), data.get('invoice_number'),
        data['amount'], data.get('issued_date'), data.get('due_date'),
        data.get('status', 'pending'), data.get('notes'), inv_id
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()))

@app.route('/api/invoices/<int:inv_id>', methods=['DELETE'])
def delete_invoice(inv_id):
    db = get_db()
    db.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Expenses ──────────────────────────────────────────────────────────────────

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    db = get_db()
    rows = db.execute("""
        SELECT e.*, j.name as job_name
        FROM expenses e
        LEFT JOIN jobs j ON e.job_id = j.id
        ORDER BY e.expense_date DESC
    """).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/expenses', methods=['POST'])
def create_expense():
    data = request.json
    db = get_db()
    cur = db.execute("""
        INSERT INTO expenses (job_id, description, amount, category, expense_date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get('job_id'), data['description'], data['amount'],
        data.get('category', 'material'), data.get('expense_date')
    ))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM expenses WHERE id=?", (cur.lastrowid,)).fetchone()))

@app.route('/api/expenses/<int:exp_id>', methods=['PUT'])
def update_expense(exp_id):
    data = request.json
    db = get_db()
    db.execute("""
        UPDATE expenses SET job_id=?, description=?, amount=?, category=?, expense_date=? WHERE id=?
    """, (data.get('job_id'), data['description'], data['amount'], data.get('category'), data.get('expense_date'), exp_id))
    db.commit()
    return jsonify(row_to_dict(db.execute("SELECT * FROM expenses WHERE id=?", (exp_id,)).fetchone()))

@app.route('/api/expenses/<int:exp_id>', methods=['DELETE'])
def delete_expense(exp_id):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    db.commit()
    return jsonify({'ok': True})

# ── Dashboard Stats ───────────────────────────────────────────────────────────

@app.route('/api/stats')
def get_stats():
    db = get_db()

    active_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE status='active'").fetchone()[0]
    completed_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE status='completed'").fetchone()[0]

    pending_invoices = db.execute("SELECT COUNT(*) FROM invoices WHERE status IN ('pending','sent')").fetchone()[0]
    overdue_invoices = db.execute("SELECT COUNT(*) FROM invoices WHERE status='overdue'").fetchone()[0]
    total_outstanding = db.execute("SELECT COALESCE(SUM(amount),0) FROM invoices WHERE status IN ('pending','sent','overdue')").fetchone()[0]

    materials_to_order = db.execute("SELECT COUNT(*) FROM materials WHERE ordered=0 AND received=0").fetchone()[0]
    materials_ordered = db.execute("SELECT COUNT(*) FROM materials WHERE ordered=1 AND received=0").fetchone()[0]

    # This month's expenses
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    monthly_expenses = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_date >= ?", (month_start,)
    ).fetchone()[0]

    return jsonify({
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'total_outstanding': total_outstanding,
        'materials_to_order': materials_to_order,
        'materials_ordered': materials_ordered,
        'monthly_expenses': monthly_expenses,
    })

if __name__ == '__main__':
    init_db()
    print("[Server] Starting ConstructionCo Micro SaaS on http://localhost:5555")
    app.run(host='0.0.0.0', port=5555, debug=True)
