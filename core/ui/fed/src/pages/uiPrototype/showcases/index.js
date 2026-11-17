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

const SHOWCASES = {
  layout: layoutShowcases,
  text: textShowcases,
  heading: headingShowcases,
  separator: separatorShowcases,
  button: buttonShowcases,
  icon: iconShowcases,
  progress: progressShowcases,
  steps: stepsShowcases,
  message: messageShowcases,
  input: inputShowcases,
};

export function getWidgetShowcase(categoryId, widgetId) {
  const Showcase = SHOWCASES[categoryId]?.[widgetId];
  return Showcase || null;
}
