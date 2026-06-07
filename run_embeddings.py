import sys, json
sys.path.insert(0, 'backend')
from vector_db import chunk_all_documents, generate_embeddings, build_vector_store

with open('data/cleaned_funds.json', encoding='utf-8') as f:
    documents = json.load(f)

# Task 1: Chunk
chunks = chunk_all_documents(documents)
print(f'Total chunks: {len(chunks)}\n')

# Task 2: Embed
embedded = generate_embeddings(chunks)
print(f'Embedded: {len(embedded)}/{len(chunks)} chunks\n')

# Task 3: Store in ChromaDB
build_vector_store(embedded)
