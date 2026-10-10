# knowledge/: RAG corpus

Curated, **verified** documents for hybrid search. One Markdown file per document with front matter:

```yaml
---
title: SSM business registration (sole proprietorship)
namespace: national        # national | sarawak | framework
publisher: Suruhanjaya Syarikat Malaysia
source_url: https://...
retrieved_on: 2026-10-10
---
```

- `national/`: SSM, SME Corp, MYStartup/Cradle, TEKUN, MARA, MOH food handler, LHDN basics
- `sarawak/`: Sarawak state agencies and programmes, local councils (DBKU, MBKS, etc.) licensing
- `frameworks/`: Business Model Canvas block definitions, council review rubric

Rules: no personal contact details (organisation contacts only); every file has a `source_url` someone opened; target ≥30 documents (PLAN Phase D).
