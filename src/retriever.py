def get_retriever(vector_store):
    retrieve = vector_store.as_retriever(search_kwangs = {"k" : 3})
    return retrieve