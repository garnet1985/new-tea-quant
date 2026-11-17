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
import progressRingDoc from 'ui/progress/progressRing/doc';
import stepperDoc from 'ui/steps/stepper/doc';
import messageDoc from 'ui/message/message/doc';
import toastDoc from 'ui/message/toast/doc';
import ntqHelpTooltipDoc from 'ui/message/ntqHelpTooltip/doc';
import fieldDoc from 'ui/input/field/doc';
import textFieldDoc from 'ui/input/textField/doc';
import textAreaDoc from 'ui/input/textArea/doc';
import checkboxDoc from 'ui/input/checkbox/doc';
import radioDoc from 'ui/input/radio/doc';
import selectDoc from 'ui/input/select/doc';
import searchSelectDoc from 'ui/input/searchSelect/doc';
import searchFieldDoc from 'ui/input/searchField/doc';
import autocompleteDoc from 'ui/input/autocomplete/doc';
import switchDoc from 'ui/input/switch/doc';
import dateDoc from 'ui/input/date/doc';
import dateRangeDoc from 'ui/input/dateRange/doc';

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
    progressRing: progressRingDoc,
  },
  steps: {
    stepper: stepperDoc,
  },
  message: {
    message: messageDoc,
    toast: toastDoc,
    ntqHelpTooltip: ntqHelpTooltipDoc,
  },
  input: {
    field: fieldDoc,
    textField: textFieldDoc,
    textArea: textAreaDoc,
    checkbox: checkboxDoc,
    radio: radioDoc,
    select: selectDoc,
    searchSelect: searchSelectDoc,
    searchField: searchFieldDoc,
    autocomplete: autocompleteDoc,
    switch: switchDoc,
    date: dateDoc,
    dateRange: dateRangeDoc,
  },
};

export function getWidgetDoc(categoryId, widgetId) {
  return DOCS[categoryId]?.[widgetId] || null;
}
