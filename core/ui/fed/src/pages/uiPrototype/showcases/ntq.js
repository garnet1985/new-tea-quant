import React, { useState } from 'react';
import PythonDictEditor from 'ui/ntq/pythonDictEditor';
import { Showcase, SampleDim, SampleRow, SampleNA } from './sample';

function AppNavShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleNA>占位：实现后对齐 views/appNav（主导航 / 高级菜单 / 设置）。</SampleNA>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="5. 外观"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
    </Showcase>
  );
}

function PageBannerShowcase() {
  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleNA>占位：实现后对齐 views/pageBanner（title / description / rightSlot）。</SampleNA>
      </SampleDim>
      <SampleDim title="2. 大小"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="3. 间距"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="4. 颜色"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
      <SampleDim title="5. 外观"><SampleNA>不适用（待实现）。</SampleNA></SampleDim>
    </Showcase>
  );
}

function PythonDictEditorShowcase() {
  const [text, setText] = useState('{\n  "alpha": 1,\n  "enabled": true\n}\n');
  const [parseError, setParseError] = useState('');
  const [errorContext, setErrorContext] = useState([]);

  const validate = () => {
    try {
      JSON.parse(text);
      setParseError('');
      setErrorContext([]);
    } catch (err) {
      const msg = err?.message || 'JSON 解析失败';
      setParseError(msg);
      const lines = String(text || '').split('\n');
      setErrorContext(
        lines.slice(0, 5).map((line, i) => ({
          lineNo: i + 1,
          text: line,
          isError: i === 0,
        })),
      );
    }
  };

  return (
    <Showcase>
      <SampleDim title="1. 形态">
        <SampleRow label="验证 + 错误上下文" block>
          <PythonDictEditor
            title="样例输入"
            value={text}
            onChange={setText}
            onApply={validate}
            onLoadDefault={() => {
              setText('{\n  "alpha": 1\n}\n');
              setParseError('');
              setErrorContext([]);
            }}
            parseError={parseError}
            errorLine={parseError ? 1 : 0}
            errorColumn={parseError ? 1 : 0}
            errorContext={errorContext}
          />
        </SampleRow>
      </SampleDim>

      <SampleDim title="2. 大小">
        <SampleNA>编辑区默认约 18 行；面板拉满父级宽度。</SampleNA>
      </SampleDim>

      <SampleDim title="3. 间距">
        <SampleNA>Block gap md；工具栏按钮 gap sm。</SampleNA>
      </SampleDim>

      <SampleDim title="4. 颜色">
        <SampleNA>错误用 Message status=error；上下文行 is-error 高亮。</SampleNA>
      </SampleDim>

      <SampleDim title="5. 外观">
        <SampleNA>surface soft + bordered；业务页可换 title / 回调。</SampleNA>
      </SampleDim>
    </Showcase>
  );
}

const ntqShowcases = {
  appNav: AppNavShowcase,
  pageBanner: PageBannerShowcase,
  pythonDictEditor: PythonDictEditorShowcase,
};

export default ntqShowcases;
