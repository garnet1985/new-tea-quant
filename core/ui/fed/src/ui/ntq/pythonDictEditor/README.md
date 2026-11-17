# pythonDictEditor

JSON / Python dict 调试面板（验证、样例、错误定位）。NTQ 特有复合组件。

```js
import PythonDictEditor from 'ui/ntq/pythonDictEditor';

<PythonDictEditor value={text} onChange={setText} onApply={validate} parseError={err} />
```

`onChange` 接收**字符串**。旧路径 `ui/input/pythonDictInputPanel` 已移除。
