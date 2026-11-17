import buttonShowcases from './button';
import layoutShowcases from './layout';
import textShowcases from './text';
import headingShowcases from './heading';
import separatorShowcases from './separator';
import iconShowcases from './icon';
import progressShowcases from './progress';
import stepsShowcases from './steps';
import messageShowcases from './message';
import inputShowcases from './input';
import ntqShowcases from './ntq';
import tagShowcases from './tag';
import tableShowcases from './table';
import metricShowcases from './metric';
import chartShowcases from './chart';
import avatarShowcases from './avatar';
import calendarShowcases from './calendar';
import { resolveCategoryId } from '../catalog';

const SHOWCASES = {
  layout: layoutShowcases,
  text: {
    ...textShowcases,
    ...headingShowcases,
    ...separatorShowcases,
  },
  button: buttonShowcases,
  display: {
    ...iconShowcases,
    ...avatarShowcases,
    ...tagShowcases,
  },
  data: {
    ...tableShowcases,
    ...chartShowcases,
    ...calendarShowcases,
    ...metricShowcases,
  },
  input: inputShowcases,
  feedback: {
    ...messageShowcases,
    ...progressShowcases,
    ...stepsShowcases,
  },
  ntq: ntqShowcases,
};

export function getWidgetShowcase(categoryId, widgetId) {
  const id = resolveCategoryId(categoryId);
  return SHOWCASES[id]?.[widgetId] || null;
}
