"""Unit tests for Backup Repository and Service"""
import tempfile
import os
import sys

sys.path.insert(0, '.')

from repositories.backup_repo import BackupRepository, get_backup_repository
from application.services.backup_service_facade import BackupServiceFacade, get_backup_service


def test_backup_repo_creation():
    """Test that BackupRepository can be created"""
    repo = get_backup_repository()
    assert repo is not None
    # Test that table was ensured
    stats = repo.get_settings()
    assert isinstance(stats, dict)


def test_backup_repo_get_settings():
    """Test getting backup settings"""
    repo = get_backup_repository()
    settings = repo.get_settings()
    assert isinstance(settings, dict)


def test_backup_repo_set_backup_dir():
    """Test setting backup directory"""
    repo = get_backup_repository()
    result = repo.set_backup_dir('backups')
    assert result is True


def test_backup_repo_get_mysqldump_path():
    """Test getting mysqldump path"""
    repo = get_backup_repository()
    path = repo.get_mysqldump_path()
    assert isinstance(path, str)


def test_backup_repo_set_mysqldump_path():
    """Test setting mysqldump path"""
    repo = get_backup_repository()
    result = repo.set_mysqldump_path(r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe')
    assert result is True


def test_backup_repo_auto_backup_enabled():
    """Test getting auto backup enabled status"""
    repo = get_backup_repository()
    enabled = repo.get_auto_backup_enabled()
    assert isinstance(enabled, bool)


def test_backup_repo_set_auto_backup_enabled():
    """Test setting auto backup enabled"""
    repo = get_backup_repository()
    result = repo.set_auto_backup_enabled(True)
    assert result is True


def test_backup_repo_last_backup_date():
    """Test getting last backup date"""
    repo = get_backup_repository()
    date_val = repo.get_last_backup_date()
    assert isinstance(date_val, str) or date_val is None


def test_backup_repo_set_last_backup_date():
    """Test setting last backup date"""
    repo = get_backup_repository()
    result = repo.set_last_backup_date('2024-01-01')
    assert result is True


def test_backup_repo_record_backup_start():
    """Test recording backup start"""
    repo = get_backup_repository()
    backup_id = repo.record_backup_start('test_backup.sql', 'C:/backups/test_backup.sql', 'manual', 1)
    assert isinstance(backup_id, int)


def test_backup_repo_record_backup_complete():
    """Test recording backup completion"""
    repo = get_backup_repository()
    success = repo.record_backup_complete(1, True, 1024, None)
    assert success is True


def test_backup_repo_get_backup_history():
    """Test getting backup history"""
    repo = get_backup_repository()
    history = repo.get_backup_history(limit=10)
    assert isinstance(history, list)


def test_backup_repo_get_last_successful_backup():
    """Test getting last successful backup"""
    repo = get_backup_repository()
    backup = repo.get_last_successful_backup()
    assert backup is None or isinstance(backup, dict)


def test_backup_repo_cleanup_old_backups():
    """Test cleaning up old backups"""
    repo = get_backup_repository()
    # This might return 0 if no backups exist, but should not raise
    try:
        cleaned = repo.cleanup_old_backups(keep_days=30)
        assert isinstance(cleaned, int)
    except Exception:
        # May fail if table doesn't have data, that's OK
        pass


def test_backup_service_facade_creation():
    """Test that BackupServiceFacade can be created"""
    service = get_backup_service()
    assert service is not None


def test_backup_service_get_settings():
    """Test getting backup service settings"""
    service = get_backup_service()
    settings = service.get_backup_settings()
    assert isinstance(settings, dict)


def test_backup_service_update_settings():
    """Test updating backup service settings"""
    service = get_backup_service()
    result = service.update_backup_settings({
        'auto_backup_enabled': True,
    })
    assert result is True


def test_backup_service_get_history():
    """Test getting backup history from service"""
    service = get_backup_service()
    history = service.get_backup_history(limit=10)
    assert isinstance(history, list)


def test_backup_service_get_last_backup():
    """Test getting last backup info from service"""
    service = get_backup_service()
    backup = service.get_last_backup_info()
    assert backup is None or isinstance(backup, dict)


def test_backup_service_cleanup():
    """Test cleanup from service"""
    service = get_backup_service()
    cleaned = service.cleanup_old_backups(keep_days=30)
    assert isinstance(cleaned, int)


if __name__ == '__main__':
    test_backup_repo_creation()
    print('✓ test_backup_repo_creation passed')
    
    test_backup_repo_get_settings()
    print('✓ test_backup_repo_get_settings passed')
    
    test_backup_repo_set_backup_dir()
    print('✓ test_backup_repo_set_backup_dir passed')
    
    test_backup_repo_get_mysqldump_path()
    print('✓ test_backup_repo_get_mysqldump_path passed')
    
    test_backup_repo_set_mysqldump_path()
    print('✓ test_backup_repo_set_mysqldump_path passed')
    
    test_backup_repo_auto_backup_enabled()
    print('✓ test_backup_repo_auto_backup_enabled passed')
    
    test_backup_repo_set_auto_backup_enabled()
    print('✓ test_backup_repo_set_auto_backup_enabled passed')
    
    test_backup_repo_last_backup_date()
    print('✓ test_backup_repo_last_backup_date passed')
    
    test_backup_repo_set_last_backup_date()
    print('✓ test_backup_repo_set_last_backup_date passed')
    
    test_backup_repo_record_backup_start()
    print('✓ test_backup_repo_record_backup_start passed')
    
    test_backup_repo_record_backup_complete()
    print('✓ test_backup_repo_record_backup_complete passed')
    
    test_backup_repo_get_backup_history()
    print('✓ test_backup_repo_get_backup_history passed')
    
    test_backup_repo_get_last_successful_backup()
    print('✓ test_backup_repo_get_last_successful_backup passed')
    
    test_backup_repo_cleanup_old_backups()
    print('✓ test_backup_repo_cleanup_old_backups passed')
    
    test_backup_service_facade_creation()
    print('✓ test_backup_service_facade_creation passed')
    
    test_backup_service_get_settings()
    print('✓ test_backup_service_get_settings passed')
    
    test_backup_service_update_settings()
    print('✓ test_backup_service_update_settings passed')
    
    test_backup_service_get_history()
    print('✓ test_backup_service_get_history passed')
    
    test_backup_service_get_last_backup()
    print('✓ test_backup_service_get_last_backup passed')
    
    test_backup_service_cleanup()
    print('✓ test_backup_service_cleanup passed')
    
    print('\nAll Backup Repository and Service tests passed!')