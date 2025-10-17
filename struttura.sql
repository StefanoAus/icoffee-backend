CREATE TABLE groups (
    name TEXT PRIMARY KEY
);

CREATE TABLE users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    group_name TEXT NOT NULL REFERENCES groups(name) ON UPDATE CASCADE ON DELETE RESTRICT,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin'))
);

CREATE TABLE menu_items (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL CHECK (category IN ('drinks', 'foods')),
    name TEXT NOT NULL,
    UNIQUE (category, name)
);

CREATE TABLE menu_options (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE (item_id, name)
);

CREATE TABLE orders (
    order_date DATE NOT NULL,
    username TEXT NOT NULL REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    group_name TEXT NOT NULL REFERENCES groups(name) ON UPDATE CASCADE ON DELETE CASCADE,
    drink_item TEXT,
    drink_variant TEXT,
    food_item TEXT,
    food_variant TEXT,
    PRIMARY KEY (order_date, username)
);

CREATE TABLE payments (
    payment_date DATE NOT NULL,
    group_name TEXT NOT NULL REFERENCES groups(name) ON UPDATE CASCADE ON DELETE CASCADE,
    payer_username TEXT NOT NULL REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (payment_date, group_name)
);

CREATE INDEX idx_users_group_name ON users(group_name);
CREATE INDEX idx_menu_items_category ON menu_items(category, name);
CREATE INDEX idx_menu_options_item ON menu_options(item_id);
CREATE INDEX idx_orders_group_date ON orders(order_date, group_name);
CREATE INDEX idx_payments_group_date ON payments(group_name, payment_date);