import ntqButtonDoc from 'ui/button/ntqButton/doc';
import rainbowButtonDoc from 'ui/button/rainbowButton/doc';
import columnDoc from 'ui/layout/column/doc';
import blockDoc from 'ui/layout/block/doc';
import sectionDoc from 'ui/layout/section/doc';
import tabsDoc from 'ui/layout/tabs/doc';
import textDoc from 'ui/text/text/doc';
import quoteDoc from 'ui/text/quote/doc';
import separatorDoc from 'ui/text/separator/doc';
import textBlockDoc from 'ui/text/textBlock/doc';
import codeBlockDoc from 'ui/text/codeBlock/doc';
import headingDoc from 'ui/text/heading/doc';
import ntqIconDoc from 'ui/icon/ntqIcon/doc';
import loadingBarsDoc from 'ui/progress/loadingBars/doc';
import loadingDoc from 'ui/progress/loading/doc';
import progressBarDoc from 'ui/progress/progressBar/doc';

const DOCS = {
  layout: {
    column: columnDoc,
    block: blockDoc,
    section: sectionDoc,
    tabs: tabsDoc,
  },
  text: {
    text: textDoc,
    quote: quoteDoc,
    textBlock: textBlockDoc,
    codeBlock: codeBlockDoc,
  },
  heading: {
    heading: headingDoc,
  },
  separator: {
    separator: separatorDoc,
  },
  button: {
    ntqButton: ntqButtonDoc,
    rainbowButton: rainbowButtonDoc,
  },
  icon: {
    ntqIcon: ntqIconDoc,
  },
  progress: {
    loadingBars: loadingBarsDoc,
    loading: loadingDoc,
    progressBar: progressBarDoc,
  },
};

export function getWidgetDoc(categoryId, widgetId) {
  return DOCS[categoryId]?.[widgetId] || null;
}
