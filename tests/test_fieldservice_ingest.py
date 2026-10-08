import base64

from src.fieldservice_ingest import WorkOrderDocument, chunk_text, make_pdf_payload


def test_chunk_text_keeps_follow_up_context_in_order():
    item = WorkOrderDocument("WO-1", "first second third fourth", [], "assigned", "check again")
    chunks = chunk_text(item.document, size=2)
    assert chunks == ["first second", "third fourth"]
    assert item.dispatch_status == "assigned"
    assert item.technician_follow_up == "check again"


def test_make_pdf_payload_returns_a_pdf_document():
    payload = base64.b64decode(make_pdf_payload("service note"))
    assert payload.startswith(b"%PDF-1.4")
    assert b"(service note) Tj" in payload
    assert int(payload.split(b"startxref\n", 1)[1].splitlines()[0]) == payload.index(b"xref\n")
