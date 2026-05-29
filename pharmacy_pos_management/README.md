# Pharmacy POS Management for Odoo 17

Enterprise pharmacy management module for Odoo 17 covering branches, products,
batches, inventory, purchases, POS orders, prescriptions, customers, accounting,
reports, scheduled alerts, and integration endpoints.

## Included
- Multi-company pharmacy profiles, branches, managers, cashboxes, and branch users
- Medicine/product master data with barcode, SKU, QR, clinical fields, attachments, alternatives, and controlled/prescription flags
- Batch and expiry tracking with FEFO selection helpers, expired-sale blocking, and cron-based alerts
- Branch inventory, adjustments, transfers, reorder thresholds, and stock states
- Purchase workflow from draft to RFQ, approval, and receipt
- Pharmacy POS orders with partial payments, hold/refund states, expiry validation, and receipt PDF
- Prescription upload, doctor data, refill flow, allergy/interactions notes
- Patient profiles, loyalty, promotions, credit, and statement lines
- Accounting integration records, analytic/cost-center fields, dashboards, reports, and APIs
- Security groups, access rights, branch record rules, chatter/activity tracking
- REST endpoints for products, stock, and report summaries

## API Endpoints
- `GET /pharmacy/api/products`
- `GET /pharmacy/api/stock`
- `GET /pharmacy/api/reports/summary`

All endpoints use `auth='user'` and respect record rules.

## Notes
External providers such as OCR, WhatsApp, SMS, payment gateways, printer bridges,
and native mobile apps require provider-specific credentials and adapters. This
module provides secure configuration records and API-ready backend surfaces.

## License
OEEL-1
