"""
缓存管理器
提供多种缓存策略和持久化选项
"""

import json
import pickle
import sqlite3
import hashlib
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
from loguru import logger


class CacheBackend(ABC):
    """缓存后端抽象基类"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """获取所有键"""
        pass


class MemoryCache(CacheBackend):
    """内存缓存后端"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """检查缓存项是否过期"""
        if 'expires_at' not in entry:
            return False
        return datetime.now() > datetime.fromisoformat(entry['expires_at'])
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if self._is_expired(entry):
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        entry = {
            'value': value,
            'created_at': datetime.now().isoformat()
        }
        
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            entry['expires_at'] = expires_at.isoformat()
        
        self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._cache and not self._is_expired(self._cache[key])
    
    def keys(self) -> List[str]:
        """获取所有有效键"""
        valid_keys = []
        expired_keys = []
        
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
            else:
                valid_keys.append(key)
        
        # 清理过期键
        for key in expired_keys:
            del self._cache[key]
        
        return valid_keys
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.keys())


class FileCache(CacheBackend):
    """文件缓存后端"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self._load_index()
    
    def _load_index(self) -> None:
        """加载缓存索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self._index = json.load(f)
            else:
                self._index = {}
        except Exception as e:
            logger.warning(f"加载缓存索引失败: {e}")
            self._index = {}
    
    def _save_index(self) -> None:
        """保存缓存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存索引失败: {e}")
    
    def _get_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用MD5哈希避免文件名过长或包含特殊字符
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """检查缓存项是否过期"""
        if 'expires_at' not in entry:
            return False
        return datetime.now() > datetime.fromisoformat(entry['expires_at'])
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._index:
            return None
        
        entry = self._index[key]
        if self._is_expired(entry):
            self.delete(key)
            return None
        
        file_path = self._get_file_path(key)
        if not file_path.exists():
            # 索引存在但文件不存在，清理索引
            del self._index[key]
            self._save_index()
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"读取缓存文件失败: {e}")
            self.delete(key)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        file_path = self._get_file_path(key)
        
        try:
            # 保存数据到文件
            with open(file_path, 'wb') as f:
                pickle.dump(value, f)
            
            # 更新索引
            entry = {
                'created_at': datetime.now().isoformat(),
                'file_path': str(file_path)
            }
            
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
                entry['expires_at'] = expires_at.isoformat()
            
            self._index[key] = entry
            self._save_index()
            
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")
            # 清理可能创建的文件
            if file_path.exists():
                file_path.unlink()
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key not in self._index:
            return False
        
        file_path = self._get_file_path(key)
        
        # 删除文件
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.error(f"删除缓存文件失败: {e}")
        
        # 删除索引
        del self._index[key]
        self._save_index()
        return True
    
    def clear(self) -> None:
        """清空所有缓存"""
        # 删除所有缓存文件
        for key in list(self._index.keys()):
            self.delete(key)
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if key not in self._index:
            return False
        
        entry = self._index[key]
        if self._is_expired(entry):
            self.delete(key)
            return False
        
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    def keys(self) -> List[str]:
        """获取所有有效键"""
        valid_keys = []
        expired_keys = []
        
        for key, entry in self._index.items():
            if self._is_expired(entry):
                expired_keys.append(key)
            else:
                file_path = self._get_file_path(key)
                if file_path.exists():
                    valid_keys.append(key)
                else:
                    expired_keys.append(key)
        
        # 清理过期或无效键
        for key in expired_keys:
            self.delete(key)
        
        return valid_keys


class SQLiteCache(CacheBackend):
    """SQLite缓存后端"""
    
    def __init__(self, db_path: str = "cache/cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)")
    
    def _cleanup_expired(self) -> None:
        """清理过期缓存"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        self._cleanup_expired()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            try:
                return pickle.loads(row[0])
            except Exception as e:
                logger.error(f"反序列化缓存值失败: {e}")
                self.delete(key)
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        try:
            serialized_value = pickle.dumps(value)
            created_at = datetime.now().isoformat()
            expires_at = None
            
            if ttl is not None:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (key, serialized_value, created_at, expires_at))
                
        except Exception as e:
            logger.error(f"保存缓存值失败: {e}")
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            return cursor.rowcount > 0
    
    def clear(self) -> None:
        """清空所有缓存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        self._cleanup_expired()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM cache WHERE key = ?", (key,))
            return cursor.fetchone() is not None
    
    def keys(self) -> List[str]:
        """获取所有有效键"""
        self._cleanup_expired()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key FROM cache")
            return [row[0] for row in cursor.fetchall()]


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, 
                 backend: Union[str, CacheBackend] = "memory",
                 default_ttl: Optional[int] = None,
                 **backend_kwargs):
        """
        初始化缓存管理器
        
        Args:
            backend: 缓存后端类型或实例 ("memory", "file", "sqlite")
            default_ttl: 默认TTL（秒）
            **backend_kwargs: 后端特定参数
        """
        self.default_ttl = default_ttl
        
        if isinstance(backend, str):
            if backend == "memory":
                self.backend = MemoryCache()
            elif backend == "file":
                self.backend = FileCache(**backend_kwargs)
            elif backend == "sqlite":
                self.backend = SQLiteCache(**backend_kwargs)
            else:
                raise ValueError(f"不支持的缓存后端: {backend}")
        else:
            self.backend = backend
        
        logger.info(f"缓存管理器初始化完成，后端: {type(self.backend).__name__}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = self.backend.get(key)
            if value is not None:
                logger.debug(f"缓存命中: {key}")
            else:
                logger.debug(f"缓存未命中: {key}")
            return value
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        try:
            effective_ttl = ttl if ttl is not None else self.default_ttl
            self.backend.set(key, value, effective_ttl)
            logger.debug(f"缓存设置: {key}, TTL: {effective_ttl}")
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            result = self.backend.delete(key)
            if result:
                logger.debug(f"缓存删除: {key}")
            return result
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        try:
            self.backend.clear()
            logger.info("缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return self.backend.exists(key)
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {e}")
            return False
    
    def keys(self) -> List[str]:
        """获取所有键"""
        try:
            return self.backend.keys()
        except Exception as e:
            logger.error(f"获取缓存键列表失败: {e}")
            return []
    
    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """
        获取缓存值，如果不存在则调用工厂函数生成并缓存
        
        Args:
            key: 缓存键
            factory_func: 工厂函数，用于生成缓存值
            ttl: TTL（秒）
            
        Returns:
            缓存值
        """
        value = self.get(key)
        if value is not None:
            return value
        
        try:
            value = factory_func()
            self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"工厂函数执行失败: {e}")
            raise
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            keys = self.keys()
            return {
                'backend_type': type(self.backend).__name__,
                'total_keys': len(keys),
                'default_ttl': self.default_ttl,
                'sample_keys': keys[:10] if keys else []
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                'backend_type': type(self.backend).__name__,
                'error': str(e)
            }


# 全局缓存实例
_global_cache: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache


def init_cache_manager(backend: Union[str, CacheBackend] = "memory", 
                      default_ttl: Optional[int] = None,
                      **backend_kwargs) -> CacheManager:
    """
    初始化全局缓存管理器
    
    Args:
        backend: 缓存后端类型或实例
        default_ttl: 默认TTL（秒）
        **backend_kwargs: 后端特定参数
        
    Returns:
        缓存管理器实例
    """
    global _global_cache
    _global_cache = CacheManager(backend, default_ttl, **backend_kwargs)
    return _global_cache