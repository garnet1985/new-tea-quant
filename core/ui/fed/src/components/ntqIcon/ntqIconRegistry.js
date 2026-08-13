import { ReactComponent as AddIcon } from './icons/add.svg';
import { ReactComponent as ArrowRightIcon } from './icons/arrow_right.svg';
import { ReactComponent as CancelIcon } from './icons/cancel.svg';
import { ReactComponent as DeleteIcon } from './icons/delete.svg';
import { ReactComponent as DownloadIcon } from './icons/download.svg';
import { ReactComponent as HelpIcon } from './icons/help.svg';
import { ReactComponent as InfoIcon } from './icons/info.svg';
import { ReactComponent as PlayIcon } from './icons/play.svg';
import { ReactComponent as PlayCircleIcon } from './icons/play_circle.svg';
import { ReactComponent as RadioUncheckedIcon } from './icons/radio_button_unchecked.svg';
import { ReactComponent as RefreshIcon } from './icons/refresh.svg';
import { ReactComponent as RemoveIcon } from './icons/remove.svg';
import { ReactComponent as SearchIcon } from './icons/search.svg';
import { ReactComponent as SentimentDissatisfiedIcon } from './icons/sentiment_dissatisfied.svg';
import { ReactComponent as SentimentSatisfiedIcon } from './icons/sentiment_satisfied.svg';
import { ReactComponent as SuccessIcon } from './icons/success.svg';
import { ReactComponent as SyncAltIcon } from './icons/sync_alt.svg';
import { ReactComponent as UploadFileIcon } from './icons/upload_file.svg';
import { ReactComponent as WarningIcon } from './icons/warning.svg';
import { ReactComponent as WebhookIcon } from './icons/webhook.svg';

/** 与 ``icons/*.svg`` 及 ``NTQ_ICON_MAP`` 的 key 对应；``expandMore`` 复用 ``arrow_right`` + 旋转。 */
export const NTQ_ICON_MAP = {
  add: AddIcon,
  cancel: CancelIcon,
  chevronRight: ArrowRightIcon,
  delete: DeleteIcon,
  download: DownloadIcon,
  expandMore: ArrowRightIcon,
  help: HelpIcon,
  info: InfoIcon,
  play: PlayIcon,
  playCircle: PlayCircleIcon,
  radioUnchecked: RadioUncheckedIcon,
  refresh: RefreshIcon,
  remove: RemoveIcon,
  search: SearchIcon,
  sentimentDissatisfied: SentimentDissatisfiedIcon,
  sentimentSatisfied: SentimentSatisfiedIcon,
  success: SuccessIcon,
  syncAlt: SyncAltIcon,
  uploadFile: UploadFileIcon,
  warning: WarningIcon,
  webhook: WebhookIcon,
};
