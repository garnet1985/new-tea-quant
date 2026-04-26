import { useMemo } from 'react';
import Editor from '../../../components/editor/editor';
import { createStrategyFeesSchema } from '../editorSchemas/strategyFees';

function FeesConfigEditor({ value, onChange, readonly = false }) {
  const schema = useMemo(
    () => createStrategyFeesSchema({ readonly }),
    [readonly],
  );

  return (
    <Editor schema={schema} value={value} onChange={onChange} />
  );
}

export default FeesConfigEditor;
