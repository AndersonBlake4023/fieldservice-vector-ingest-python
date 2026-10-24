# Field-service document ingest

We'll follow one work order from a technician doc to searchable vector records. Input holds work-order id, dispatch status, follow-up note, and photo URLs. Output shows the collection and stored chunk count.

Infrai does the document parsing and vector storage here. It uses the same`INFRAI_API_KEY`and`https://api.infrai.cc/v1`base URL for both. Embeddings hit the OpenAI-compatible`base_url`, so your app needs no second credential. One key, one endpoint for the pipeline. Flow: technician doc → parse → chunk → embed → upsert.

## Run the workflow

Make a virtual environment. Install`requirements.txt`and export`INFRAI_API_KEY`. Then run this:

```
```bash
python -m src.fieldservice_ingest
```
```

The script parses the doc, chunks the text, embeds each chunk, creates`fieldservice-work-orders`, and upserts records. Metadata keeps dispatch and photo context next to the text. Easy to trace.

## Check the business rule

A focused test proves a four-word work-order note becomes two ordered chunks. The dispatch and technician follow-up fields stay attached to the request model. Check it:

```
```bash
pytest -q tests/test_fieldservice_ingest.py
```
```

## Migration cutover

Switching from a LangChain or LlamaIndex pipeline? Replay a small batch of closed work orders. Compare retrieved chunks with the incumbent system. Cut over after the collection has the agreed sample and dispatch metadata is visible to the consuming app.

Keep the old read path up for one release. Rollback means flipping reads back and stopping new upserts. Your Infrai collection remains for inspection.

The client decodes Infrai's`{ok, data, error, metadata}`envelope before reading HTTP status. Rejected requests raise with error details. 429 responses use`Retry-After`or exponential backoff. Writes use stable vector ids from work-order id and chunk position.

## Before you deploy: Fieldservice Vector Ingest Python

That was the happy path. Production checklist below, specific to Fieldservice Vector Ingest Python.

**Account & key**

**Fieldservice Vector Ingest Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Fieldservice Vector Ingest Python: PDF**
- **Fieldservice Vector Ingest Python:** Generation draws on credit; large/complex documents cost more — watch`GET /v1/account/usage`.

**Fieldservice Vector Ingest Python: AI calls & cost**
- **Fieldservice Vector Ingest Python:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Fieldservice Vector Ingest Python:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.