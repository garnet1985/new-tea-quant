# monthCalendar

月历壳（周一～日）。

```js
import MonthCalendar from 'ui/calendar/monthCalendar';

<MonthCalendar
  year={2026}
  month={4}
  selected="2026-04-10"
  today="2026-04-08"
  density="sm"
  onMonthChange={setYm}
  onDayClick={setSelected}
/>
```

业务事件用 `renderDay`；工具见 `ui/calendar/monthUtils`。
