# 🧾 Inventory Management System (Flask + MySQL)

## 📘 Overview

This application is a **comprehensive inventory management system** built using **Flask** and  **MySQL** , designed to manage and automate business operations from purchasing and production to sales and stock tracking. It provides real-time insights and traceability through QR-code integration.

---

## 🏗️ Tech Stack

| Component          | Technology                 |
| ------------------ | -------------------------- |
| Backend Framework  | Flask (Python)             |
| Database           | MySQL                      |
| Authentication     | Flask-Login                |
| Frontend           | Jinja2 + Bootstrap         |
| Data Export        | Pandas (Excel export)      |
| QR Code Generation | qrcode + base64            |
| Deployment Example | DigitalOcean Managed MySQL |

---

## ⚙️ Core Features

### 👤 User & Role Management

* Secure authentication with Flask-Login
* Roles: `admin`, `purchase`, `general`
* Role-based access control for sensitive operations
* Dynamic role updates

### 🧾 Purchase Management

* Create and manage **purchase orders** (采购单)
* Link suppliers and invoices
* Auto-link with inventory-in workflow
* Export purchase data by date range (`/download_purchase`)

### 🧪 Production Management

* Create **production batches** (`BCHYYYYMMDD-XXX`)
* Manage raw material usage and outputs
* Generate **QR codes** for traceability
* Export production records and print batch details

### 💰 Sales Management

* Auto-generate **sales IDs** (`POYYYYMMDDNNN`)
* Record client, representative, tax, and payment details
* Track sales lifecycle:
  * `0` = 未付款 (Unpaid)
  * `1` = 已付款未出库 (Paid, Pending Shipment)
  * `2` = 已出库 (Completed)
  * `3` = 已删除 (Deleted)
* Edit, delete, restore, or download sales orders

### 📦 Inventory Management

* **Inventory-In** : manage incoming stock from purchases, production, or returns (`INYYYYMMDDNNN`)
* **Inventory-Out** : handle outbound shipments and update tracking (`OUTYYYYMMDDNNN`)
* Real-time stock updates via `source_track` table
* FIFO logic for batch-based inventory selection
* QR-based traceability system

### 🧮 Stocktaking (盘点)

* Compare actual vs system inventory
* Automatically adjust quantities and record diffs
* Update quantities in `source_track`
* Export stock adjustment logs by date

### 📊 Reporting & Export

All key operations (purchase, sales, production, inventory) can be exported to Excel (`.xlsx`) using Pandas for offline analysis.

---

## 🗄️ Database Structure (Simplified)

| Category       | Tables                                                                                                           |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| Authentication | `users`                                                                                                        |
| Product Info   | `products`,`sales_list`                                                                                      |
| Purchasing     | `purchase`,`purchase_order`                                                                                  |
| Production     | `produce`,`produce_order`                                                                                    |
| Sales          | `sale`,`sale_order`,`payments`                                                                             |
| Inventory      | `inventory`,`inventory_in`,`inventory_in_order`,`inventory_out`,`inventory_out_order`,`source_track` |
| Stocktaking    | `inventory_update`,`inventory_update_order`                                                                  |

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.10+
* MySQL Server
* Pipenv or virtualenv for dependency isolation

### 2. Installation

```bash
git clone <repo_url>
cd inventory_system
pip install -r requirements.txt
```

### 3. Environment Setup

Update MySQL credentials in `app.py`:

```python
app.config['MYSQL_HOST'] = 'your_mysql_host'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'your_user'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'inventory_system'
```

For local development:

```python
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
```

### 4. Database Initialization

Create the database in MySQL:

```sql
CREATE DATABASE inventory_system CHARACTER SET utf8mb4;
```

Import the schema SQL file if provided.

### 5. Run the Application

```bash
flask run
```

Visit the app at: **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## 🔐 User Roles

| Role         | Permissions                                 |
| ------------ | ------------------------------------------- |
| `admin`    | Full system access                          |
| `purchase` | Manage purchases, production, and inventory |
| `general`  | View and manage sales only                  |

---

## 📤 Data Export

All data views support Excel export. Common endpoints:

| Function           | Endpoint                       |
| ------------------ | ------------------------------ |
| Purchase Orders    | `/download_purchase`         |
| Production Data    | `/download_produce`          |
| Sales Orders       | `/download_sale_orders`      |
| Inventory In       | `/download_inventory_in`     |
| Inventory Out      | `/download_inventory_out`    |
| Stock Update Logs  | `/download_inventory_update` |
| Inventory Snapshot | `/download_inventory`        |

---

## 🧩 API & Utility Endpoints

| Endpoint                                            | Purpose                               |
| --------------------------------------------------- | ------------------------------------- |
| `/generate_sale_id/<year>/<month>/<day>`          | Auto-generate sale ID                 |
| `/generate_inventory_in_id/<year>/<month>/<day>`  | Generate inventory-in ID              |
| `/generate_inventory_out_id/<year>/<month>/<day>` | Generate inventory-out ID             |
| `/generate_produce_source`                        | Auto-generate production batch code   |
| `/generate_qrcode/<source_id>`                    | Generate QR code for traceability     |
| `/get_fifo_sources/<sku>/<qty>`                   | Retrieve FIFO batch sources for a SKU |

---

## 🧪 Example Workflow

1. **Create Purchase Order** → `/purchase_order`
2. **Receive Goods (Inventory In)** → `/inventory_in`
3. **Initiate Production** → `/produce_order`
4. **Create Sale Order** → `/sale_order`
5. **Mark as Paid** → `/mark_sale_paid/<sale_id>`
6. **Ship Out (Inventory Out)** → `/inventory_out`
7. **Stock Reconciliation** → `/inventory_order`
8. **Download Reports** → `/download_sale_orders`, `/download_inventory_out`, etc.

---

## 🛡️ Security Recommendations

* Replace `app.secret_key` and DB credentials with environment variables before deployment.
* Restrict uploads to `.xls` and `.xlsx` formats.
* Use HTTPS and secure session management in production.
* Regularly back up the MySQL database.

---

## 🧰 Utilities & Conventions

* **Auto ID patterns:** `INYYYYMMDDNNN`, `OUTYYYYMMDDNNN`, `POYYYYMMDDNNN`, `BCHYYYYMMDD-XXX`
* **QR Codes:** Base64-encoded PNGs generated per `source_id`
* **FIFO Tracking:** Source-based quantity deduction from earliest batch
* **Excel Export:** All exports generated dynamically with Pandas

---

## 📸 Screenshots *(optional)*

> Add UI previews such as:
>
> * Login Page
> * Purchase Order Form
> * Production Print Sheet with QR Code
> * Inventory Dashboard

---

## 📜 License

Licensed under the  **MIT License** . You are free to use, modify, and distribute this software for personal or commercial purposes.
