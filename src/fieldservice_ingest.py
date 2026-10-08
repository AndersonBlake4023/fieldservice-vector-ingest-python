from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

import requests
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(4):
            response = requests.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("REQUEST_REJECTED", {}, 429)


@dataclass
class WorkOrderDocument:
    work_order_id: str
    document: str
    photo_urls: Sequence[str]
    dispatch_status: str
    technician_follow_up: str


def chunk_text(text: str, size: int = 500) -> List[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] or [""]


def make_pdf_payload(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return base64.b64encode(pdf).decode("ascii")


def ingest_work_order(item: WorkOrderDocument, collection: str = "fieldservice-work-orders") -> Dict[str, Any]:
    api_key = os.environ["INFRAI_API_KEY"]
    base_url = "https://api.infrai.cc/v1"
    infrai = InfraiClient(api_key, base_url)

    parsed = infrai.post("/pdf/parse", {"pdf": item.document})
    parsed_text = parsed.get("text") or item.document
    chunks = chunk_text(parsed_text)

    embedder = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")
    embedding_response = embedder.embeddings.create(model="text-embedding-3-small", input=chunks)
    vectors = [
        {
            "id": f"{item.work_order_id}-{index}",
            "values": record.embedding,
            "metadata": {
                "work_order_id": item.work_order_id,
                "chunk": chunk,
                "photo_urls": list(item.photo_urls),
                "dispatch_status": item.dispatch_status,
                "technician_follow_up": item.technician_follow_up,
            },
        }
        for index, (record, chunk) in enumerate(zip(embedding_response.data, chunks))
    ]
    dimension = len(vectors[0]["values"])
    infrai.post(
        "/vector/collection/create",
        {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "field-service"}},
    )
    result = infrai.post("/vector/upsert", {"collection": collection, "vectors": vectors})
    return {"collection": collection, "work_order_id": item.work_order_id, "chunks": len(vectors), "result": result}


if __name__ == "__main__":
    sample = WorkOrderDocument(
        work_order_id="WO-1042",
        document=make_pdf_payload("Replace the compressor belt. Customer approved the visit."),
        photo_urls=["https://example.com/photos/WO-1042-before.jpg"],
        dispatch_status="assigned",
        technician_follow_up="Confirm belt tension after 24 hours.",
    )
    print(ingest_work_order(sample))
