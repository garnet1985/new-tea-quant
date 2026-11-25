import React, { useState } from 'react';
import Message from 'ui/message/message';
import Dialog from 'ui/message/dialog';
import ToastHost, { showToast } from 'ui/message/toast';
import HelpTooltip from 'ui/message/helpTooltip';
import Button from 'ui/button/button';
import Section from 'ui/layout/section';
import Block from 'ui/layout/block';
import Text from 'ui/text/text';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function MessageShowcase() {
  const [open, setOpen] = useState(true);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="inline"：圆角 + border + 底色，无 bar' block>
          <Message status="info">内容区提示：圆角卡片，不带左侧色条。</Message>
        </SampleRow>
        <SampleRow label='variant="banner"：有 bar、无圆角（header 下通栏）' block>
          <Block bordered padding="none" gap="none" radius="none">
            <div className="ui-prototype__message-banner-demo-bar ntq-muted">
              Header 区域示意
            </div>
            <Message status="warning" variant="banner">
              全局提示：左侧色条，直角通栏。
            </Message>
            <div className="ui-prototype__message-banner-demo-body ntq-muted">
              页面内容…
            </div>
          </Block>
        </SampleRow>
        <SampleRow label="可关闭（onClose）" block>
          {open ? (
            <Message status="success" onClose={() => setOpen(false)}>
              配置已更新。可点右侧关闭。
            </Message>
          ) : (
            <Button
              variant="glass"
              size="small"
              onClick={() => setOpen(true)}
            >
              重新显示
            </Button>
          )}
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无独立
          {' '}
          <Text variant="code">size</Text>
          ；图标固定
          {' '}
          <Text variant="code">xl</Text>
          （2rem），与文案垂直居中；内边距
          {' '}
          <Text variant="code">1rem</Text>
          。更大用
          {' '}
          <Text variant="code">Icon size="xxl"</Text>
          （3rem）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          内部 padding / gap 由样式固定；与兄弟块的上下距交给父级
          {' '}
          <Text variant="code">gap</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="状态 status（图标固定）" block>
          <Section gap="sm">
            <Message status="success">success · 绿</Message>
            <Message status="error">error · 红</Message>
            <Message status="warning">warning · 黄</Message>
            <Message status="info">info · 青</Message>
          </Section>
        </SampleRow>
        <SampleRow label="颜色 color（icon 可传或省略）" block>
          <Section gap="sm">
            <Message color="green">green · 无图标</Message>
            <Message color="error">error · 无图标</Message>
            <Message color="warning">warning · 无图标</Message>
            <Message color="muted">muted · 白/中性</Message>
            <Message color="cyan" icon="settings">cyan + icon</Message>
            <Message color="violet" icon="chat">violet + icon</Message>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          inline：圆角、全边框、无 bar。banner：左侧 bar、无圆角。无独立
          {' '}
          <Text variant="code">radius</Text>
          {' '}
          参数。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function DialogShowcase() {
  const [open, setOpen] = useState(false);
  const [dangerOpen, setDangerOpen] = useState(false);

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="确认弹层（title + body + actions）" block>
          <Button variant="glass" size="small" onClick={() => setOpen(true)}>
            打开说明 Dialog
          </Button>
          <Dialog
            open={open}
            onClose={() => setOpen(false)}
            title="同步说明"
            size="md"
            actions={(
              <Button variant="primary" onClick={() => setOpen(false)}>
                知道了
              </Button>
            )}
          >
            <p className="ntq-muted">
              用于需要用户明确应答的说明。轻量提示请用 Message / Toast。
            </p>
          </Dialog>
        </SampleRow>
        <SampleRow label="危险确认（取消 + danger）" block>
          <Button variant="danger" size="small" onClick={() => setDangerOpen(true)}>
            打开危险确认
          </Button>
          <Dialog
            open={dangerOpen}
            onClose={() => setDangerOpen(false)}
            title="确认清理缓存？"
            size="sm"
            actions={(
              <>
                <Button variant="ghost" onClick={() => setDangerOpen(false)}>
                  取消
                </Button>
                <Button variant="danger" onClick={() => setDangerOpen(false)}>
                  确认清理
                </Button>
              </>
            )}
          >
            <p className="ntq-muted">将清理所选缓存，此操作不可撤销。</p>
          </Dialog>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleRow label='size="sm" | "md" | "lg"'>
          <Text variant="code">sm</Text>
          <span className="ntq-muted">窄确认</span>
          <Text variant="code">md</Text>
          <span className="ntq-muted">说明</span>
          <Text variant="code">lg</Text>
          <span className="ntq-muted">较宽</span>
        </SampleRow>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          标题 / 正文 / 操作区内边距由组件固定；与页面其它块无关（模态层）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          面板走
          {' '}
          <Text variant="code">--ui-surface-panel</Text>
          ；语义靠 actions 里的
          {' '}
          <Text variant="code">Button variant</Text>
          （primary / danger / ghost）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          圆角
          {' '}
          <Text variant="code">md</Text>
          + 细描边；遮罩点击与 Esc 触发
          {' '}
          <Text variant="code">onClose</Text>
          。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function ToastShowcase() {
  return (
    <Showcase>
      <ToastHost />
      <SampleDim title="1. 形态">
        <SampleRow label="右下角弹出（点击触发）" block>
          <Section gap="sm">
            <p className="ntq-muted" style={{ margin: 0 }}>
              应用壳挂载
              {' '}
              <Text variant="code">ToastHost</Text>
              ，业务调用
              {' '}
              <Text variant="code">showToast</Text>
              。本页已本地挂载宿主以便演示。
            </p>
            <div className="ui-prototype__sample-stage">
              <Button
                variant="glass"
                size="small"
                onClick={() => showToast({ status: 'info', content: '信息 Toast' })}
              >
                info
              </Button>
              <Button
                variant="glass"
                size="small"
                onClick={() => showToast({ status: 'success', content: '已保存' })}
              >
                success
              </Button>
              <Button
                variant="glass"
                size="small"
                onClick={() => showToast({ status: 'warning', content: '配额即将用尽' })}
              >
                warning
              </Button>
              <Button
                variant="glass"
                size="small"
                onClick={() => showToast({
                  status: 'error',
                  content: '网络异常',
                  duration: 4000,
                })}
              >
                error（4s）
              </Button>
            </div>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          宿主宽度
          {' '}
          <Text variant="code">min(26.25rem, 100vw - 2rem)</Text>
          ；无独立 size 参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          固定距视口右下
          {' '}
          <Text variant="code">md</Text>
          （含安全区）；无 gap 参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          与 Message
          {' '}
          <Text variant="code">status</Text>
          {' '}
          相同：success / error / warning / info。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          玻璃底 + 模糊；可手动关闭或
          {' '}
          <Text variant="code">duration</Text>
          {' '}
          后自动消失。同一时间只展示一条。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function NtqHelpTooltipShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='variant="help" | "info" | "warning"'>
          <span className="ntq-muted">字段说明</span>
          <HelpTooltip title="默认问号：补充字段含义或用法。" />
          <span className="ntq-muted">更多信息</span>
          <HelpTooltip
            title="信息类提示，可放稍长说明。"
            variant="info"
          />
          <span className="ntq-muted">注意</span>
          <HelpTooltip
            title="有风险或需特别留意时使用。"
            variant="warning"
          />
        </SampleRow>
        <SampleRow label="shine 扫光">
          <span className="ntq-muted">强调可点</span>
          <HelpTooltip
            title="带扫光，用于需要引起注意的帮助入口。"
            shine
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          图标固定
          {' '}
          <Text variant="code">md</Text>
          ，无 size / iconSize 参数。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          触发器无额外 gap；与旁边文字的间距由父级布局控制。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          触发图标继承字色；气泡为深色玻璃底。无独立 tone 参数（形态用
          {' '}
          <Text variant="code">variant</Text>
          ）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label='placement="top" | "bottom" | "left" | "right"'>
          <HelpTooltip title="上方（默认）" placement="top" />
          <HelpTooltip title="下方" placement="bottom" />
          <HelpTooltip title="左侧" placement="left" />
          <HelpTooltip title="右侧" placement="right" />
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const messageShowcases = {
  message: MessageShowcase,
  dialog: DialogShowcase,
  toast: ToastShowcase,
  helpTooltip: NtqHelpTooltipShowcase,
};

export default messageShowcases;
