from typing import List, Any
import gc

class ChunkedProcessor:
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    async def process_in_chunks(self, items: List[Any], processor_func) -> List[Any]:
        results = []
        for i in range(0, len(items), self.chunk_size):
            chunk = items[i:i + self.chunk_size]
            chunk_results = await processor_func(chunk)
            results.extend(chunk_results)
            gc.collect()  # Wymuś garbage collection
        return results 