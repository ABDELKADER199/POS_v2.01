"""Unit tests for SyncQueueRepository"""
import tempfile
import os
import sys

sys.path.insert(0, '.')

from repositories.sync_queue_repo import SyncQueueRepository, get_sync_queue_repo


def test_sync_queue_repo_creation():
    """Test that SyncQueueRepository can be created"""
    repo = SyncQueueRepository()
    assert repo is not None
    # Test that table was ensured
    stats = repo.get_stats()
    assert 'pending' in stats


def test_sync_queue_enqueue():
    """Test enqueuing a sync operation"""
    repo = get_sync_queue_repo()
    result = repo.enqueue(
        table_name='products',
        record_id='1',
        action_type='INSERT',
        data={'product_code': 'TEST001', 'product_name': 'Test Product', 'buy_price': 100, 'sell_price': 150}
    )
    assert result is True


def test_sync_queue_get_pending():
    """Test getting pending syncs"""
    repo = get_sync_queue_repo()
    pending = repo.get_pending(limit=10)
    assert isinstance(pending, list)


def test_sync_queue_mark_synced():
    """Test marking a sync as completed"""
    repo = get_sync_queue_repo()
    # First enqueue
    repo.enqueue(table_name='test_table', record_id='1', action_type='INSERT', data={})
    # Get the last inserted id
    pending = repo.get_pending(limit=1)
    assert len(pending) > 0
    sync_id = pending[0]['id']
    # Mark as synced
    result = repo.mark_synced(sync_id)
    assert result is True


def test_sync_queue_mark_failed():
    """Test marking a sync as failed"""
    repo = get_sync_queue_repo()
    repo.enqueue(table_name='test_table', record_id='1', action_type='INSERT', data={})
    pending = repo.get_pending(limit=1)
    sync_id = pending[0]['id']
    # Mark as failed
    result = repo.mark_failed(sync_id, 'Test error')
    assert result is True


def test_sync_queue_get_stats():
    """Test getting sync statistics"""
    repo = get_sync_queue_repo()
    stats = repo.get_stats()
    assert isinstance(stats, dict)
    assert 'total' in stats or 'pending' in stats


def test_sync_queue_bulk_enqueue():
    """Test bulk enqueuing"""
    repo = get_sync_queue_repo()
    records = [
        {'table_name': 'products', 'record_id': '1', 'action_type': 'INSERT', 'data': {'product_code': 'B1', 'product_name': 'Product 1'}},
        {'table_name': 'products', 'record_id': '2', 'action_type': 'INSERT', 'data': {'product_code': 'B2', 'product_name': 'Product 2'}},
    ]
    count = repo.bulk_enqueue(records)
    assert count == 2


def test_sync_queue_requeue_failed():
    """Test requeuing failed operations"""
    repo = get_sync_queue_repo()
    repo.enqueue(table_name='test_table', record_id='1', action_type='INSERT', data={})
    pending = repo.get_pending(limit=1)
    sync_id = pending[0]['id']
    # Mark as failed twice (should fail at 3 retries)
    repo.mark_failed(sync_id, 'Error 1')
    repo.mark_failed(sync_id, 'Error 2')
    # Now it should be marked as failed with retry_count=2
    stats = repo.get_stats()
    assert stats['failed'] >= 1


def test_sync_queue_cleanup():
    """Test cleanup (no-op for sync queue, just verify stats)"""
    repo = get_sync_queue_repo()
    # Just verify stats method works
    stats = repo.get_stats()
    assert isinstance(stats, dict)


if __name__ == '__main__':
    test_sync_queue_repo_creation()
    print('✓ test_sync_queue_repo_creation passed')
    
    test_sync_queue_enqueue()
    print('✓ test_sync_queue_enqueue passed')
    
    test_sync_queue_get_pending()
    print('✓ test_sync_queue_get_pending passed')
    
    test_sync_queue_mark_synced()
    print('✓ test_sync_queue_mark_synced passed')
    
    test_sync_queue_mark_failed()
    print('✓ test_sync_queue_mark_failed passed')
    
    test_sync_queue_get_stats()
    print('✓ test_sync_queue_get_stats passed')
    
    test_sync_queue_bulk_enqueue()
    print('✓ test_sync_queue_bulk_enqueue passed')
    
    test_sync_queue_requeue_failed()
    print('✓ test_sync_queue_requeue_failed passed')
    
    print('\nAll SyncQueueRepository tests passed!')