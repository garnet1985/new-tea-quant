"""测试 Data Contract 导入和基本功能"""
import sys
sys.path.insert(0, '/Users/garnet/Desktop/new-tea-quant')

try:
    # 测试导入新的类名
    from core.modules.data_contract.core.base.base_contract import BaseDataContract, ContractMeta, ContractRuntime
    from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
    from core.modules.data_contract.core.base.base_time_series_contract import BaseTimeSeriesContract
    from core.modules.data_contract.core.base.base_non_time_series_contract import BaseNonTimeSeriesContract
    from core.modules.data_contract.core.discovery.contract_issuer import ContractIssuer
    
    print('✅ 基类导入成功')
    print('  - BaseDataContract')
    print('  - BaseDataContractLoader')
    print('  - BaseTimeSeriesContract')
    print('  - BaseNonTimeSeriesContract')
    print('  - ContractIssuer')
    
    # 测试 ContractIssuer 功能
    issuer = ContractIssuer()
    issuer.discover()
    keys = issuer.list_available_keys()
    print(f'\n✅ 发现机制工作正常：发现 {len(keys)} 个 contracts')
    
    # 测试获取 contract
    if keys:
        test_key = keys[0]
        contract = issuer.get_contract(test_key)
        print(f'\n✅ 成功获取 contract: {contract.meta.key}')
        print(f'  - Contract ID: {contract.contract_id}')
        print(f'  - Type: {contract.meta.type}')
        print(f'  - Scope: {contract.meta.scope}')
        print(f'  - Is Customized: {contract.is_customized}')
        
        # 测试时间序列 contract 的特殊方法
        if isinstance(contract, BaseTimeSeriesContract):
            print(f'  - 是时间序列 contract')
            # 测试 normalize_as_of
            normalized = contract.normalize_as_of("2020-01-01")
            print(f'  - normalize_as_of("2020-01-01") = {normalized}')
    
    print('\n✅ 所有测试通过！命名修正完成。')
    
except Exception as e:
    print(f'❌ 测试失败: {e}')
    import traceback
    traceback.print_exc()