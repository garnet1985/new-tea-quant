import { splitAssistantReply, stripDisclaimer, REPLY_DISCLAIMER } from './splitAssistantReply';

describe('splitAssistantReply', () => {
  it('strips hard disclaimer from body', () => {
    const raw = [
      '结论如下。',
      '',
      '以上仅为研究思路与工具辅助结果，不构成投资建议；请自行验证，新茶不对结果负责。',
      '',
      '[下一步]',
      '帮我对照止盈止损再跑一遍',
    ].join('\n');
    const out = splitAssistantReply(raw);
    expect(out.body).toContain('结论如下');
    expect(out.body).not.toContain('以上仅为研究思路');
    expect(out.suggestions).toEqual(['帮我对照止盈止损再跑一遍']);
    expect(REPLY_DISCLAIMER).toContain('参考建议');
  });

  it('strips soft disclaimer line', () => {
    const { body, found } = stripDisclaimer(
      '正文\n\n新茶提供的仅仅是参考建议，无法为您的结果负责哦。',
    );
    expect(found).toBe(true);
    expect(body).toBe('正文');
  });
});
