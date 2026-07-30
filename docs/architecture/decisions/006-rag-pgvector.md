# ADR-006: RAG con pgvector Integrado en PostgreSQL

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

La base de conocimiento requiere búsqueda semántica (RAG) para que la IA responda con información específica de cada empresa. Necesitamos almacenar y buscar embeddings vectoriales de forma eficiente.

## Decisión

Usar **pgvector** (extensión de PostgreSQL) como vector store, en lugar de bases de datos vectoriales dedicadas como Pinecone, Weaviate o Qdrant.

## Alternativas Consideradas

| Opción | Pros | Contras |
|--------|------|---------|
| Pinecone | Managed, escalable, rápido | Vendor lock-in, costo alto, otra infraestructura |
| Weaviate | Open source, auto-hosted | Otro servicio que operar, complejidad |
| Qdrant | Performance excelente | Otra DB que mantener, sin transacciones ACID |
| **pgvector** | Ya tenemos PostgreSQL, transaccional, multi-tenant nativo | Menor performance en billones de vectores |

## Justificación

- Eliminamos un servicio de la infraestructura (menos complejidad operacional)
- Los embeddings participan en las mismas transacciones que el resto de datos
- El tenant_id se aplica naturalmente (mismo RLS que el resto)
- Para el volumen esperado (miles de documentos por tenant, no millones), pgvector es más que suficiente
- HNSW indexes en pgvector ofrecen búsqueda ANN con latencia sub-10ms para <1M vectores
- Si el volumen crece exponencialmente, se puede migrar a Qdrant sin cambiar la interfaz

## Implementación

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    metadata JSONB
);

CREATE INDEX ix_chunks_embedding 
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

## Consecuencias

- Limitado a ~5M vectores por tabla antes de degradar performance
- Necesitamos gestionar dimensiones diferentes si se cambia de modelo de embeddings
- El backup de vectores está incluido en el backup de PostgreSQL (ventaja)
- No tenemos filtering pre-vector search nativo (se hace con WHERE + vector search)
