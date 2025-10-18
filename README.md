# Flask Inventory Management System

A full-featured, role-based inventory and order management web application built with **Flask** and **MySQL**.
This app enables you to handle purchasing, production, sales, and inventory tracking in one place — with authentication, QR code traceability, FIFO logic, and Excel data exports.

---

## Features

### Authentication & Roles

- Secure login via **Flask-Login**.
- Supports dynamic role switching (`admin`, `purchase`, `general`).
- Role-based access decorator: `@role_required('admin', 'purchase', ...)`.

### Purchasing

- Create and manage purchase orders.
- Auto-generates unique purchase IDs.
- Upload Excel product lists for bulk management.
- Export purchase data to Excel.

### Production

- Generate **production batch IDs** like `BCHYYYYMMDD-XXX`.
- Print production orders with QR codes.
- Integrates production records into the inventory system.

### Sales

- Create and manage sales orders with auto-generated IDs (`POYYYYMMDDNNN`).
- Update status: unpaid / paid / shipped / deleted.
- Edit, restore, and export orders easily.

### Inventory Management

- Manage **inbound** and **outbound** inventory transactions.
- Auto-generate `INYYYYMMDDNNN` and `OUTYYYYMMDDNNN` codes.
- FIFO-based picking: fetch source IDs in first-in-first-out order.
- View and export inventory snapshots.
- Audit updates via cycle count (`inventory_update`).

### Excel Exports

Export all records (purchases, production, inventory in/out, and updates) as `.xlsx` files for audits or reports.

### QR Code Traceability

- Generates per-batch and per-source QR codes (`/generate_qrcode/<source_id>`).
- QR embedded in printable documents for production and inventory orders.

---

## Tech Stack

| Component      | Technology                     |
| -------------- | ------------------------------ |
| Backend        | Flask                          |
| Database       | MySQL                          |
| Authentication | Flask-Login                    |
| File Handling  | Pandas, XlsxWriter             |
| QR Codes       | `qrcode` + Base64 encoding   |
| Excel Export   | Pandas `.to_excel()`         |
| Deployment     | Gunicorn / Nginx (recommended) |

---

## Project Structure

app.py               # Main Flask application

templates/           # HTML templates

uploads/             # Uploaded Excel files

static/              # Static files (CSS, JS)
