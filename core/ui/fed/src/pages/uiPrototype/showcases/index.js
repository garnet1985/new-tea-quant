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

const SHOWCASES = {
  layout: layoutShowcases,
  text: textShowcases,
  heading: headingShowcases,
  separator: separatorShowcases,
  button: buttonShowcases,
  tag: tagShowcases,
  table: tableShowcases,
  icon: iconShowcases,
  progress: progressShowcases,
  steps: stepsShowcases,
  message: messageShowcases,
  input: inputShowcases,
  ntq: ntqShowcases,
  metric: metricShowcases,
};

export function getWidgetShowcase(categoryId, widgetId) {
  const Showcase = SHOWCASES[categoryId]?.[widgetId];
  return Showcase || null;
}
