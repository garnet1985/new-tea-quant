/** 数据契约列表：`/advanced/data-contracts` */
export function matchDataContractList(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  return path === '/advanced/data-contracts';
}

export const DATA_CONTRACT_LIST_HELP = {
  id: 'data-contract-list',
  version: 2,
  trigger: 'enter',
  match: matchDataContractList,
  steps: [
    {
      pages: [
        {
          title: '数据契约',
          body: '「数据契约」是定义好的一种数据结构。当前界面只读，并列出了所有数据契约的唯一标识 key，方便查找和使用。',
        },
      ],
    },
    {
      target: 'data-contract-list-rediscover',
      pages: [
        {
          title: '重新发现',
          body: '如果你在 userspace 里扩展了新的数据契约，点这里刷新重新发现即可，不必重启应用。',
        },
      ],
    },
    {
      target: 'data-contract-list-key',
      pages: [
        {
          title: 'Key',
          body: '数据契约的唯一标识。其他模块声明了这个 key，就能准确注入对应数据，从而避免手写取数代码。',
        },
      ],
    },
    {
      target: 'data-contract-list-origin',
      pages: [
        {
          title: '来源',
          body: '区分这项契约是系统自带，还是用户扩展接入的。',
        },
      ],
    },
    {
      target: 'data-contract-list-time-series',
      pages: [
        {
          title: '时序',
          body: '标明当前数据是不是沿着一条时间线组织的。',
        },
      ],
    },
    {
      target: 'data-contract-list-per-entity',
      pages: [
        {
          title: '按实体',
          body: '区分数据是全局共享，还是每个实体私有。例如 GDP 是全局的，而 K 线是每只股票各自一份。',
        },
      ],
    },
  ],
};
