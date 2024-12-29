import pytest
from app.utils.memory_management import ChunkedProcessor

@pytest.fixture
def processor():
    return ChunkedProcessor(chunk_size=2)

@pytest.mark.asyncio
async def test_process_in_chunks_empty_list(processor):
    async def mock_processor(items):
        return items
    
    result = await processor.process_in_chunks([], mock_processor)
    assert result == []

@pytest.mark.asyncio
async def test_process_in_chunks_single_chunk(processor):
    test_data = [1, 2]
    
    async def mock_processor(items):
        return [x * 2 for x in items]
    
    result = await processor.process_in_chunks(test_data, mock_processor)
    assert result == [2, 4]

@pytest.mark.asyncio
async def test_process_in_chunks_multiple_chunks(processor):
    test_data = [1, 2, 3, 4, 5]
    
    async def mock_processor(items):
        return [x * 2 for x in items]
    
    result = await processor.process_in_chunks(test_data, mock_processor)
    assert result == [2, 4, 6, 8, 10]

@pytest.mark.asyncio
async def test_process_in_chunks_custom_size():
    processor = ChunkedProcessor(chunk_size=3)
    test_data = [1, 2, 3, 4, 5]
    processed_chunks = []
    
    async def mock_processor(items):
        processed_chunks.append(len(items))
        return [x * 2 for x in items]
    
    result = await processor.process_in_chunks(test_data, mock_processor)
    assert result == [2, 4, 6, 8, 10]
    assert processed_chunks == [3, 2]  # First chunk: 3 items, Second chunk: 2 items

@pytest.mark.asyncio
async def test_process_in_chunks_with_objects():
    processor = ChunkedProcessor(chunk_size=2)
    class TestObj:
        def __init__(self, value):
            self.value = value
    
    test_data = [TestObj(1), TestObj(2), TestObj(3)]
    
    async def mock_processor(items):
        return [item.value * 2 for item in items]
    
    result = await processor.process_in_chunks(test_data, mock_processor)
    assert result == [2, 4, 6] 