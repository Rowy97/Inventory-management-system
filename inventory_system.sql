CREATE DATABASE IF NOT EXISTS inventory_system;
USE inventory_system;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'purchase', 'general') NOT NULL DEFAULT 'general'
);

-- Sales list table
CREATE TABLE IF NOT EXISTS sales_list (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sales_name VARCHAR(50) NOT NULL UNIQUE,
    username VARCHAR(50) UNIQUE
);

INSERT INTO users (username, password, role)
VALUES ('longspring001', 'LongSpring1ventory', 'admin');

-- Inventory table
CREATE TABLE IF NOT EXISTS inventory (
    product_sku VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    quantity INT NOT NULL
);

-- Source tracking
CREATE TABLE IF NOT EXISTS source_track (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_sku VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL,
    status INT DEFAULT 0,
    source_id VARCHAR(50) UNIQUE NOT NULL
);

-- Product SKU list
CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(20) PRIMARY KEY,
    item VARCHAR(100) NOT NULL
);

-- Sale (Header)
CREATE TABLE IF NOT EXISTS sale (
    sale_id VARCHAR(20) PRIMARY KEY,
    sale_date DATE NOT NULL,
    client VARCHAR(50) NOT NULL,
    rep VARCHAR(20) NOT NULL,
    delivery_way VARCHAR(20) NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    grand_total DECIMAL(8,2) NOT NULL,
    invoice VARCHAR(10),
    delivery_fee DECIMAL(8,2) NOT NULL,
    tax DECIMAL(8,2) NOT NULL,
    tax_rate DECIMAL(8,2) NOT NULL,
    amount_received DECIMAL(8,2) NOT NULL,
    amount_remained DECIMAL(8,2) GENERATED ALWAYS AS (grand_total - amount_received) STORED,
    status INT DEFAULT 0
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    invoice VARCHAR(10) NOT NULL,
    amount DECIMAL(8,2) NOT NULL,          
    payment_date DATE NOT NULL,     
    payment_method VARCHAR(30) NOT NULL
);

-- Sale Order (Content)
CREATE TABLE IF NOT EXISTS sale_order (
    sale_id VARCHAR(20) NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    product_name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(8,2) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(8,2) NOT NULL,
    note VARCHAR(50),
    status INT DEFAULT 0,
    PRIMARY KEY (sale_id, product_sku),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Produce (Header)
CREATE TABLE IF NOT EXISTS produce (
    produce_id INT PRIMARY KEY AUTO_INCREMENT,
    production_date DATE NOT NULL,
    produce_source VARCHAR(20) NOT NULL UNIQUE,
    product_name VARCHAR(100) NOT NULL,
    product_sku VARCHAR(20) NOT NULL,
    sale_id VARCHAR(20),
    plan_quantity INT NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    status INT NOT NULL DEFAULT 0,
    status2 INT NOT NULL DEFAULT 0,
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Produce Order (Materials)
CREATE TABLE IF NOT EXISTS produce_order (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    material_sku VARCHAR(20), 
    material_name VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    produce_source VARCHAR(20) NOT NULL

);

-- Purchase (Header)
CREATE TABLE IF NOT EXISTS purchase (
    purchase_id INT PRIMARY KEY AUTO_INCREMENT,
    purchase_date DATE NOT NULL,
    supplier VARCHAR(50),
    invoice VARCHAR(50),
    price DECIMAL(8,2) NOT NULL,
    pay_way VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL
);

-- Purchase Order (Content)
CREATE TABLE IF NOT EXISTS purchase_order (
    purchase_id INT NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    product_name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(8,2) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(8,2) NOT NULL,
    delivery_fee DECIMAL(8,2) NOT NULL,
    PRIMARY KEY (purchase_id, product_sku),
    FOREIGN KEY (purchase_id) REFERENCES purchase(purchase_id),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Inventory In (Header)
CREATE TABLE IF NOT EXISTS inventory_in (
    inventory_in_id VARCHAR(20) PRIMARY KEY,
    in_type VARCHAR(50) NOT NULL, 
    date DATE NOT NULL,
    corresponding_order VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL
);

-- Inventory In Order (Content)
CREATE TABLE IF NOT EXISTS inventory_in_order (
    inventory_in_id VARCHAR(20) NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    product_name VARCHAR(100) NOT NULL,
    ideal_quantity INT NOT NULL,
    true_quantity INT NOT NULL,
    diff INT NOT NULL,
    source_id VARCHAR(50) NOT NULL,
    notes VARCHAR(100),
    PRIMARY KEY (inventory_in_id, product_sku),
    FOREIGN KEY (inventory_in_id) REFERENCES inventory_in(inventory_in_id),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Inventory Out (Header)
CREATE TABLE IF NOT EXISTS inventory_out (
    inventory_out_id VARCHAR(20) PRIMARY KEY,
    date DATE NOT NULL,
    corresponding_order VARCHAR(50) NOT NULL,
    invoice VARCHAR(20) NOT NULL,
    client VARCHAR(50) NOT NULL,
    delivery_way VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL
);

-- Inventory Out Order (Content)
CREATE TABLE IF NOT EXISTS inventory_out_order (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inventory_out_id VARCHAR(20) NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    ideal_total_quantity INT NOT NULL,
    true_quantity INT NOT NULL,
    note VARCHAR(100),
    source_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (inventory_out_id) REFERENCES inventory_out(inventory_out_id),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Exchange Return (Header)
CREATE TABLE IF NOT EXISTS exchange_return (
    exchange_return_id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    client VARCHAR(50) NOT NULL,
    rep VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL
);

-- Exchange Return Order (Content)
CREATE TABLE IF NOT EXISTS exchange_return_order (
    exchange_return_id INT NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    product_name VARCHAR(100) NOT NULL,
    unit_price DECIMAL(6,2) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(8,2) NOT NULL,
    original_date DATE NOT NULL,
    reviewer VARCHAR(20) NOT NULL,
    PRIMARY KEY (exchange_return_id, product_sku),
    FOREIGN KEY (exchange_return_id) REFERENCES exchange_return(exchange_return_id),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);

-- Inventory Update (Header)
CREATE TABLE IF NOT EXISTS inventory_update (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    user_name VARCHAR(50) NOT NULL
);

-- Inventory Update Order (Content)
CREATE TABLE IF NOT EXISTS inventory_update_order (
    update_id INT PRIMARY KEY AUTO_INCREMENT,
    source_id VARCHAR(50) NOT NULL,
    product_sku VARCHAR(20) NOT NULL, 
    product_name VARCHAR(100) NOT NULL,
    inventory_quantity INT NOT NULL,
    true_quantity INT NOT NULL,
    diff INT NOT NULL,
    note VARCHAR(100),
    FOREIGN KEY (update_id) REFERENCES inventory_update(id),
    FOREIGN KEY (product_sku) REFERENCES products(sku)
);
