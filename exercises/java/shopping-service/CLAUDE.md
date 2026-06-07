# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application (available at http://localhost:8080/shopping)
./grailsw run-app

# Run all tests
./grailsw test-app

# Run only unit tests
./grailsw test-app unit:

# Run a single test class
./grailsw test-app unit: s2gx.OrderSpec

# Compile without running
./grailsw compile
```

## Architecture

This is a **Grails 2.4.3** (Groovy) REST shopping application. It was written in 2014 to demonstrate Grails REST features and is intentionally legacy — a target for modernization exercises.

### Domain Model

```
Customer ──hasMany──> Order ──hasMany──> OrderLine ──> Product
```

- `Customer`, `Order`, `Product` are annotated with `@Resource`, which auto-generates RESTful controllers and URL mappings.
- `OrderLine` belongs to `Order` but has no `@Resource`; it is managed via `OrderLineController`.
- `Order` maps to a table named `orders` (reserved word workaround) and eager-fetches `orderLines`.
- `Order.getPrice()` sums `orderLines*.price`; `OrderLine.getPrice()` is `quantity * product.price`.

### REST Endpoints

Defined in `grails-app/conf/UrlMappings.groovy`:

| Path | Notes |
|------|-------|
| `/products` | Full CRUD via `@Resource` |
| `/customers` | Full CRUD via `@Resource` (JSON + XML) |
| `/orders` | Full CRUD via explicit `OrderController` |
| `/customers/{id}/orders` | Nested resource mapping |

All responses support content negotiation via `Accept` header or `.json`/`.xml` extension suffixes. See `curl_samples.txt` for working request examples.

### Key Files

- `grails-app/conf/BootStrap.groovy` — seeds sample data (3 products, 1 customer, 2 orders) on startup
- `grails-app/conf/DataSource.groovy` — H2 in-memory DB; `create-drop` in dev, `update` in test/prod
- `src/groovy/s2gx/OrderXmlRenderer.groovy` — custom XML renderer using `MarkupBuilder`
- `src/groovy/s2gx/client_demo.groovy` — standalone Groovy REST client using `http-builder`

### Testing

Tests use the **Spock** framework with Grails test mixins (`@TestFor`). Unit tests mock domain constraints via `mockForConstraintsTests()`. Test reports land in `target/test-reports/`.
