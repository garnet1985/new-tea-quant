# dateRange

日期区间，`value={{ start, end }}`。

```js
import DateRange from 'ui/input/dateRange';

<DateRange
  label="回测区间"
  value={{ start, end }}
  onChange={(e) => {
    setStart(e.target.value.start);
    setEnd(e.target.value.end);
  }}
/>
```
