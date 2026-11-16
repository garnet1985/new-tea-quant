import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Text from 'ui/text/text';
import Quote from 'ui/text/quote';
import TextBlock from 'ui/text/textBlock';
import CodeBlock from 'ui/text/codeBlock';
import Section from 'ui/layout/section';
import NtqIcon from 'ui/icon/ntqIcon';
import { HEADING_BAR_TOKENS, TEXT_VARIANTS } from 'ui/tokens';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

const DEMO_SNIPPET = `function greet(name) {
  return \`hello, \${name}\`;
}`;

function TextShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="普通文字（不包本组件；父级 gap = 1rem）" block>
          <Section>
            <p>正文直接写段落，继承全局字色与行高。</p>
            <p className="ntq-muted">次要说明用 .ntq-muted</p>
            <p className="ntq-caption">图注用 .ntq-caption</p>
            <span className="ntq-label">字段名 .ntq-label</span>
          </Section>
        </SampleRow>
        <SampleRow label="行内链接 .ntq-link（按钮样式链接用 NtqButton + href）" block>
          <Section>
            <p>
              见
              {' '}
              <a className="ntq-link" href="#text-link-demo">文字规范</a>
              {' '}
              与路由
              {' '}
              <RouterLink className="ntq-link" to="/dev/ui/heading">
                标题图鉴
                <NtqIcon name="chevronRight" size="sm" />
              </RouterLink>
            </p>
            <p>
              <button type="button" className="ntq-link">
                <NtqIcon name="folderOpen" size="sm" />
                按钮伪装链接（少用）
              </button>
            </p>
          </Section>
        </SampleRow>
        <SampleRow label={`行内特殊字形 variant：${TEXT_VARIANTS.join(' | ')}`} block>
          <Section>
            <p>
              路径
              {' '}
              <Text variant="code">userspace/strategies/demo</Text>
              {' '}
              与路由
              {' '}
              <Text variant="code">/dev/ui</Text>
            </p>
            <p>
              品牌短词
              {' '}
              <Text variant="rainbow">New Tea Quant</Text>
            </p>
            <p>
              句中强调
              {' '}
              <Text variant="accent">仅此一词</Text>
              {' '}
              即可。
            </p>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          本组件无
          {' '}
          <Text variant="code">size</Text>
          ；代码字继承上下文字号。链接同理；图标建议
          {' '}
          <Text variant="code">size=&quot;sm&quot;</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          行内组件，无
          {' '}
          <Text variant="code">gap</Text>
          。链接与图标间距由
          {' '}
          <Text variant="code">.ntq-link</Text>
          的
          {' '}
          <Text variant="code">gap</Text>
          管。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label="由形态自带配色；链接为青色" block>
          <p>
            <Text variant="rainbow">彩虹字</Text>
            {' · '}
            <Text variant="accent">强调字</Text>
            {' · '}
            <Text variant="code">等宽代码</Text>
            {' · '}
            <a className="ntq-link" href="#text-link-color">链接</a>
          </p>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="代码字：等宽 + 青色，无底无边；链接默认无下划线，悬停出现" block>
          <Section>
            <p>
              行内
              {' '}
              <Text variant="code">mono + cyan</Text>
              {' '}
              不做成块。
            </p>
            <p>
              <a className="ntq-link" href="#text-link-appearance">悬停看下划线</a>
            </p>
          </Section>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

function QuoteShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="固定样式：整体四周 margin 空隙 + 轻白底 + 白条 + 斜体" block>
          <Quote>
            优先用语义 token，不要在调用处写死像素。
          </Quote>
        </SampleRow>
        <SampleRow label="多段引用（同款样式）" block>
          <Quote>
            <p>第一句：组件 API 只收语义名。</p>
            <p>第二句：改视觉数值去覆盖 CSS 变量。</p>
          </Quote>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>固定样式，无 size 变体；字号继承正文。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>内边距固定，无 padding 变体；与外层间距由 Section/Block gap 管。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>无颜色变体；竖条白色、底轻微白色。提示/警告用 TextBlock。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>外观固定（白条 + 轻白底 + 斜体），无 surface / radius 参数。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function CodeBlockShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label='默认 variant="glass"（科技玻璃；可带语言标注）' block>
          <CodeBlock language="js">{DEMO_SNIPPET}</CodeBlock>
        </SampleRow>
        <SampleRow label='变种 variant="soft"（轻底，适合嵌在已有玻璃面板里）' block>
          <CodeBlock variant="soft" language="bash">{`npm run start`}</CodeBlock>
        </SampleRow>
        <SampleRow label="无语言标注" block>
          <CodeBlock>{`const ready = true;`}</CodeBlock>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无
          {' '}
          <Text variant="code">size</Text>
          ；字号固定等宽
          {' '}
          <Text variant="code">sm</Text>
          。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>
          内边距固定；
          {' '}
          <Text variant="code">language</Text>
          落在上 padding 带内，不与代码重叠。
        </SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>
          无独立色参；表面由
          {' '}
          <Text variant="code">variant</Text>
          决定（glass / soft）。
        </SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>
          圆角 / 描边固定。后续 input 等也按「默认玻璃 + 一个变种」收敛。语法高亮暂未接入。
        </SampleNA>
      </SampleDim>
    </Showcase>
  );
}

function TextBlockShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="摘要说明（图鉴组件摘要同款）" block>
          <TextBlock bar="cyan" surface="soft">
            行内特殊字形用 Text；多行代码用 CodeBlock；本组件只做说明性文本块。
          </TextBlock>
        </SampleRow>
        <SampleRow label="警告说明" block>
          <TextBlock bar="warning" surface="soft">
            <ul>
              <li>不要用文本块冒充标题。</li>
              <li>上方已有竖条标题时，下方用普通 Block 即可。</li>
            </ul>
          </TextBlock>
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>
          无
          {' '}
          <Text variant="code">size</Text>
          ；字号继承 / 用内容自身样式。
        </SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleRow label='padding="sm" | "md"' block>
          <Section gap="sm">
            <TextBlock bar="cyan" surface="soft" padding="sm">内边距较小</TextBlock>
            <TextBlock bar="cyan" surface="soft" padding="md">内边距默认</TextBlock>
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleRow label={`bar：${HEADING_BAR_TOKENS.filter(Boolean).join(' | ')}`} block>
          <Section gap="sm">
            {HEADING_BAR_TOKENS.filter(Boolean).map((tone) => (
              <TextBlock key={tone} bar={tone} surface="soft" padding="sm">
                {`bar="${tone}"`}
              </TextBlock>
            ))}
          </Section>
        </SampleRow>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleRow label="surface + radius（右侧圆角）" block>
          <Section gap="sm">
            <TextBlock bar="cyan" surface="panel" radius="md">panel 表面</TextBlock>
            <TextBlock bar="violet" surface="gradient" radius="lg">gradient 表面</TextBlock>
          </Section>
        </SampleRow>
      </SampleDim>
    </Showcase>
  );
}

const textShowcases = {
  text: TextShowcase,
  quote: QuoteShowcase,
  textBlock: TextBlockShowcase,
  codeBlock: CodeBlockShowcase,
};

export default textShowcases;
