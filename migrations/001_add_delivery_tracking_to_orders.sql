ALTER TABLE orders
    ADD COLUMN delivery_agent_id INT NULL AFTER call_center_user_id,
    ADD COLUMN delivery_status ENUM('Unassigned', 'Assigned', 'PickedUp', 'OutForDelivery', 'Delivered', 'Failed') NOT NULL DEFAULT 'Unassigned' AFTER status,
    ADD COLUMN delivery_assigned_at DATETIME NULL AFTER delivery_status,
    ADD COLUMN delivery_notes TEXT NULL AFTER delivery_assigned_at;

CREATE INDEX idx_orders_delivery_agent ON orders (delivery_agent_id);
CREATE INDEX idx_orders_delivery_status ON orders (delivery_status);

ALTER TABLE orders
    ADD CONSTRAINT fk_orders_delivery_agent
    FOREIGN KEY (delivery_agent_id) REFERENCES users(id)
    ON DELETE SET NULL;