# API Examples

This guide shows an end-to-end API flow using `curl`.

Base URL used below:

- `http://127.0.0.1:8010`

## 1) Login and get access token

```bash
curl -X POST "http://127.0.0.1:8010/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Expected response includes:

```json
{
  "access_token": "<token>",
  "token_type": "bearer"
}
```

Export token for later requests:

```bash
export TOKEN="<token>"
```

PowerShell:

```powershell
$TOKEN = "<token>"
```

## 2) Create warehouse

```bash
curl -X POST "http://127.0.0.1:8010/warehouses" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Warehouse",
    "location": "Durban"
  }'
```

## 3) Create product

Create a product with zero opening stock:

```bash
curl -X POST "http://127.0.0.1:8010/products" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "SKU-100",
    "name": "Industrial Solvent",
    "quantity_on_hand": 0,
    "warehouse_id": 1
  }'
```

## 4) Stock IN twice (create FIFO lots)

```bash
curl -X POST "http://127.0.0.1:8010/stock-movements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "movement_type": "IN",
    "quantity": 100,
    "note": "First batch"
  }'
```

```bash
curl -X POST "http://127.0.0.1:8010/stock-movements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "movement_type": "IN",
    "quantity": 50,
    "note": "Second batch"
  }'
```

## 5) Stock OUT using FIFO

This should consume the oldest lot first:

```bash
curl -X POST "http://127.0.0.1:8010/stock-movements" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "movement_type": "OUT",
    "quantity": 80,
    "note": "Dispatch to customer"
  }'
```

## 6) Inspect lots

```bash
curl "http://127.0.0.1:8010/products/1/lots"
```

## 7) View audit trail filters

By product:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8010/stock-movements?product_id=1"
```

By date range (ISO-8601):

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8010/stock-movements?date_from=2026-04-01T00:00:00&date_to=2026-04-30T23:59:59"
```

## OpenAPI client generation

OpenAPI schema URL:

- `http://127.0.0.1:8010/openapi.json`

TypeScript example with OpenAPI Generator:

```bash
openapi-generator-cli generate \
  -i http://127.0.0.1:8010/openapi.json \
  -g typescript-fetch \
  -o generated/ts-client
```

Python example:

```bash
openapi-generator-cli generate \
  -i http://127.0.0.1:8010/openapi.json \
  -g python \
  -o generated/python-client
```
