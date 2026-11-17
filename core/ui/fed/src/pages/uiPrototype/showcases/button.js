import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import NtqButton from 'ui/button/ntqButton';
import RainbowButton from 'ui/button/rainbowButton';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function NtqButtonShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant：glass | primary | attention | ghost'>
          <NtqButton variant="glass">玻璃</NtqButton>
          <NtqButton variant="primary">主要</NtqButton>
          <NtqButton variant="attention">强调</NtqButton>
          <NtqButton variant="ghost">轻量</NtqButton>
        </SampleRow>
        <SampleRow label='图标：前置 / 后置 iconPlacement="start" | "end"'>
          <NtqButton variant="glass" icon="add">前置添加</NtqButton>
          <NtqButton variant="primary" icon="chevronRight" iconPlacement="end">下一步</NtqButton>
          <NtqButton variant="ghost" icon="arrowBack" iconPlacement="start">返回</NtqButton>
        </SampleRow>
        <SampleRow label="纯图标（无文案；需 tooltip 或 aria-label）">
          <NtqButton icon="settings" tooltip="设置" aria-label="设置" />
          <NtqButton variant="primary" icon="add" tooltip="添加" aria-label="添加" />
          <NtqButton variant="ghost" icon="delete" tooltip="删除" aria-label="删除" />
          <NtqButton variant="glass" size="small" icon="search" tooltip="搜索" aria-label="搜索" />
        </SampleRow>
        <SampleRow label="按钮样式超链接（href / RouterLink；行内文字链仍用 .ntq-link）">
          <NtqButton href="#button-link-demo" icon="folderOpen">锚点链接</NtqButton>
          <NtqButton component={RouterLink} to="/dev/ui/text" icon="chevronRight" iconPlacement="end">
            文字图鉴
          </NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="small" 与默认；iconSize 语义档位'>
          <NtqButton variant="glass" size="small" icon="search" iconSize="sm">搜索</NtqButton>
          <NtqButton variant="glass" icon="add" iconSize="md">添加</NtqButton>
          <NtqButton variant="primary" icon="settings" iconSize="lg">设置</NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          按钮本身无
          {' '}
          <Text variant="code">gap</Text>
          ；组间距由外层布局负责。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="由形态决定，无独立色调参数">
          <NtqButton variant="primary">主要（实心）</NtqButton>
          <NtqButton variant="attention">强调（描边）</NtqButton>
          <NtqButton variant="glass">玻璃</NtqButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="tooltip；禁用态（禁用仍可悬停看说明）">
          <NtqButton variant="glass" tooltip="保存当前草稿">悬停看说明</NtqButton>
          <NtqButton variant="primary" disabled tooltip="权限不足">不可用</NtqButton>
          <NtqButton variant="glass" disabled>不可用</NtqButton>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function RainbowButtonShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='shape="circle" · 图标 / 标记'>
          <RainbowButton icon="play" aria-label="运行" />
          <RainbowButton icon="refresh" aria-label="刷新" />
          <RainbowButton mark="help" size="lg" aria-label="帮助" />
          <RainbowButton mark="ai" size="lg" glow aria-label="助手" />
        </SampleRow>
        <SampleRow label='shape="pill"（胶囊）'>
          <RainbowButton shape="pill" ring="spin" icon="play" shimmer>
            开始运行
          </RainbowButton>
          <RainbowButton shape="pill" ring="plain">
            取消
          </RainbowButton>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='圆形：size="sm" | "lg"'>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" size="sm" aria-label="小" />
            <Text variant="code">sm</Text>
          </div>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" size="lg" aria-label="大" />
            <Text variant="code">lg</Text>
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">gap</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="glow 脉冲光晕；quiet 同款光晕但不闪">
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton mark="ai" size="lg" ring="still" glow aria-label="发光" />
            <Text variant="code">glow</Text>
          </div>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton mark="ai" size="lg" ring="still" glow quiet aria-label="安静" />
            <Text variant="code">quiet</Text>
          </div>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='ring="spin" | "still" | "plain"'>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" ring="spin" aria-label="旋转环" />
            <Text variant="code">spin</Text>
          </div>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton icon="play" ring="still" aria-label="静止环" />
            <Text variant="code">still</Text>
          </div>
          <div className="ui-prototype__icon-size-cell">
            <RainbowButton icon="cancel" ring="plain" aria-label="无环" />
            <Text variant="code">plain</Text>
          </div>
        </SampleRow>
        <SampleRow label="胶囊 + 禁用">
          <RainbowButton shape="pill" ring="spin" disabled>
            排队中
          </RainbowButton>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const buttonShowcases = {
  ntqButton: NtqButtonShowcase,
  rainbowButton: RainbowButtonShowcase,
};

export default buttonShowcases;
