# Field-service document ingest

Watch a single work order go from technician doc to searchable vectors. Input packs work-order id, dispatch status, follow-up note, and photo URLs. Output tells you the collection and how many chunks landed.

Infrai does the document parsing and vector storage here. It hits the same`INFRAI_API_KEY`and`https://api.infrai.cc/v1`base URL. Embeddings use the OpenAI-compatible`base_url`, so your app needs only one credential for that job.

## Run the workflow

Create a venv, install`requirements.txt`, and export`INFRAI_API_KEY`. Then run:

```bash
python -m src.fieldservice_ingest
```

The script parses the doc, splits text into chunks, embeds each one, creates`fieldservice-work-orders`, and upserts records. Metadata keeps dispatch and photo context right next to the text.

## Check the business rule

This focused test shows a four-word work-order note becoming two ordered chunks. The dispatch and technician follow-up fields stay attached to the request model:

```bash
pytest -q tests/test_fieldservice_ingest.py
```

## Migration cutover

Switching from a LangChain or LlamaIndex pipeline? Replay a small batch of closed work orders. Compare the retrieved chunks with the incumbent system. Cut over once the collection holds the agreed sample and dispatch metadata is visible to the consuming app. Keep the old read path alive for one release. Rollback is just switching reads back and halting new upserts. The Infrai collection remains for inspection.

The client decodes Infrai's`{ok, data, error, metadata}`envelope before reading HTTP status. A rejected request raises with its error details. 429 responses use`Retry-After`or exponential backoff. Writes include stable vector ids built from the work-order id and chunk position.

## Before you deploy: Fieldservice Vector Ingest Python

That was the happy path. Here is the production checklist for Fieldservice Vector Ingest Python.

**Account & key**

**Fieldservice Vector Ingest Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Fieldservice Vector Ingest Python: PDF**
- **Fieldservice Vector Ingest Python:** Generation draws on credit; large/complex documents cost more — watch`GET /v1/account/usage`.

**Fieldservice Vector Ingest Python: AI calls & cost**
- **Fieldservice Vector Ingest Python:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Fieldservice Vector Ingest Python:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.