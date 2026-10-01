# Screen Ticket Insights (EDA)

A Streamlit dashboard that explores Adonmo's screen-failure tickets. It covers two areas:
**failure insights** and **operational insights**.

## Run it

The ticket data is company-internal and is **not in this repo**. Put the export at
`data/ticket_dump.xlsx` before running.

```
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Files

| File | What it does |
|---|---|
| `data/ticket_dump.xlsx` | The raw ticket export. To refresh the dashboard, replace this file with a new export that has the same columns. |
| `data_prep.py` | Loads the Excel file, cleans it, and adds helper columns: cause group, part/area, location, stage, and so on. |
| `app.py` | The dashboard itself (filters, KPIs, 4 tabs). |
| `.streamlit/config.toml` | Theme (colours, font). |

## Key definitions

- **Ticket** = one `OPEN` or `REOPEN` row. The raw file has several rows per ticket (opened, worked on, monitored, closed).
- **Cause group** = `component_issue_code` folded into 5 buckets: Society (RWA), Internet, Not reproducible, Hardware, Other.
- **Site-wide outage** = 3 or more screens at the same site opening a ticket in the same second.
- **Response time** is approximate. There is no ticket ID, so events are linked by following each screen's timeline.
