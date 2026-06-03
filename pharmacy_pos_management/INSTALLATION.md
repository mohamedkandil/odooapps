# Installation Guide

## Requirements
- Odoo 17 Community or Enterprise
- PostgreSQL supported by your Odoo deployment
- Standard Odoo addons: `stock`, `purchase`, `account`, `point_of_sale`, `mail`, `barcodes`

## Install
1. Copy `pharmacy_pos_management` into an Odoo addons path.
2. Restart Odoo.
3. Update the Apps List.
4. Install **Pharmacy POS Management**.
5. Assign users to one of the pharmacy groups and set their allowed pharmacy branches on the user form.

## Optional Docker
```bash
docker build -t pharmacy_pos_management .
docker run -p 8069:8069 pharmacy_pos_management
```

## Production Notes
- Configure real accounting journals, warehouses, taxes, and payment methods.
- Configure integration endpoint records for WhatsApp, SMS, payment gateway, printers, and mobile clients.
- Review record rules for your branch/company policy before go-live.
