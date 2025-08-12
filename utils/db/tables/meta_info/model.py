import json
from utils.db.db_model import BaseTableModel

class MetaInfoModel(BaseTableModel):
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True

    def _parse_info(self, info_str):
        """解析info字符串为字典"""
        if not info_str:
            return {}
        
        try:
            # 尝试解析为JSON格式
            return json.loads(info_str)
        except json.JSONDecodeError:
            # 如果不是JSON格式，尝试解析旧的管道分隔格式
            info_dict = {}
            items = info_str.split('|')
            for item in items:
                if '=' in item:
                    key, value = item.split('=', 1)
                    info_dict[key.strip()] = value.strip()
            return info_dict

    def _serialize_info(self, info_dict):
        """将字典序列化为JSON字符串"""
        return json.dumps(info_dict, ensure_ascii=False)

    def get_meta_info(self, key: str):
        """获取指定key的meta信息"""
        info = self.load_one()
        if info is None:
            return None
        
        info_dict = self._parse_info(info['info'])
        return info_dict.get(key)

    def set_meta_info(self, key: str, value: str):
        """设置指定key的meta信息，保持其他key不变"""
        info = self.load_one()
        
        if info is None:
            # 如果记录不存在，创建新记录
            info_dict = {key: value}
            self.insert_one({'info': self._serialize_info(info_dict)})
        else:
            # 如果记录存在，更新指定key，保持其他key不变
            info_dict = self._parse_info(info['info'])
            info_dict[key] = value
            
            # 使用基类的 update 方法
            self.update(
                {'info': self._serialize_info(info_dict)},
                'id = %s',
                (info['id'],)
            )

    def get_all_meta_info(self):
        """获取所有meta信息"""
        info = self.load_one()
        if info is None:
            return {}
        
        return self._parse_info(info['info'])

    def set_all_meta_info(self, info_dict):
        """设置所有meta信息（会覆盖现有数据）"""
        info = self.load_one()
        
        if info is None:
            self.insert_one({'info': self._serialize_info(info_dict)})
        else:
            # 使用基类的 update 方法
            self.update(
                {'info': self._serialize_info(info_dict)},
                'id = %s',
                (info['id'],)
            )

    # 为了向后兼容，保留旧的方法名
    def get_meta_info_by_key(self, key: str):
        return self.get_meta_info(key)
    
    def set_meta_info_by_key(self, key: str, value: str):
        return self.set_meta_info(key, value)

