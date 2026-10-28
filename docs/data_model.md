# Data model

### UML
Three entities: **customer**, **order** and **barcode** are needed based on below business flow assumption:
- A customer places orders.
- An order has zero or more barcodes once tickets are issued. 
- A barcode is a single ticket code and is unique across the whole system. Until it is sold, it has no order.

```mermaid
erDiagram
    direction LR

    CUSTOMER ||--o{ ORDER : "places"
    ORDER ||--o{ BARCODE : "contains"

    CUSTOMER {
        text customer_id PK
    }

    ORDER {
        text order_id PK
        text customer_id FK
    }

    BARCODE {
        text barcode PK
        text order_id FK "nullable when unsold"
    }
```

### Indexes

| Index | Query it serves |
| --- | --- |
| `orders` primary key `(order_id)` | fetch the customer for a barcode's order |
| `orders_customer_id_idx` on `(customer_id)` | all orders for a customer, and the top-customers aggregate |
| `barcodes` primary key `(barcode)` | uniqueness and lookup of one code |
| `barcodes_order_id_idx` on `(order_id)` | voucher join from an order to its barcodes |

### Example Schemas in PostgreSQL
```sql
CREATE TABLE customers (
    customer_id text PRIMARY KEY, -- primary key is indexed
);

CREATE TABLE orders (
    order_id text PRIMARY KEY,
    customer_id text NOT NULL REFERENCES customers (customer_id),
    CONSTRAINT orders_id_not_blank CHECK (btrim(order_id) <> '')
);

CREATE INDEX orders_customer_id_idx ON orders (customer_id);

CREATE TABLE barcodes (
    barcode text PRIMARY KEY, -- indexed
    order_id text REFERENCES orders (order_id) ON DELETE RESTRICT,
);

CREATE INDEX barcodes_order_id_idx ON barcodes (order_id);
```