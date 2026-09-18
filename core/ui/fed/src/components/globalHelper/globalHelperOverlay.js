import React from 'react';
import PropTypes from 'prop-types';
import { Button, IconButton } from '@mui/material';
import NtqIcon from 'components/ntqIcon/ntqIcon';

function GlobalHelperOverlay({
  hole = null,
  cardStyle = null,
  cardRef = null,
  title = '',
  body = '',
  image = '',
  stepLabel = '',
  isFirst = true,
  isLast = true,
  onPrev = () => {},
  onNext = () => {},
  onSkip = () => {},
}) {
  return (
    <div className="ntq-global-helper" role="dialog" aria-modal="true" aria-label="页面引导">
      <div className="ntq-global-helper__blocker" />
      {hole ? (
        <div
          className="ntq-global-helper__spot"
          style={{
            left: `${hole.left}px`,
            top: `${hole.top}px`,
            width: `${hole.width}px`,
            height: `${hole.height}px`,
          }}
          aria-hidden
        />
      ) : (
        <div className="ntq-global-helper__dim" aria-hidden />
      )}
      <div
        ref={cardRef}
        className="ntq-global-helper__card"
        style={cardStyle || undefined}
      >
        <div className="ntq-global-helper__card-head">
          {stepLabel ? (
            <p className="ntq-global-helper__step">{stepLabel}</p>
          ) : null}
          <IconButton
            className="ntq-global-helper__close"
            onClick={onSkip}
            aria-label="跳过引导"
            size="small"
            disableRipple
          >
            <NtqIcon name="cancel" size={18} />
          </IconButton>
        </div>
        {title ? <h2 className="ntq-global-helper__title">{title}</h2> : null}
        {body ? <p className="ntq-global-helper__body">{body}</p> : null}
        {image ? (
          <img className="ntq-global-helper__image" src={image} alt="" />
        ) : null}
        <div className="ntq-global-helper__actions">
          <Button
            variant="text"
            className="ntq-global-helper__skip"
            onClick={onSkip}
            disableRipple
          >
            跳过
          </Button>
          <div className="ntq-global-helper__nav">
            <Button
              variant="outlined"
              className="ntq-global-helper__prev"
              onClick={onPrev}
              disabled={isFirst}
              disableRipple
            >
              上一步
            </Button>
            <Button
              variant="contained"
              className="ntq-global-helper__next"
              onClick={onNext}
              disableRipple
            >
              {isLast ? '我知道了' : '下一步'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

GlobalHelperOverlay.propTypes = {
  hole: PropTypes.shape({
    left: PropTypes.number,
    top: PropTypes.number,
    width: PropTypes.number,
    height: PropTypes.number,
  }),
  cardStyle: PropTypes.object,
  cardRef: PropTypes.oneOfType([
    PropTypes.func,
    PropTypes.shape({ current: PropTypes.any }),
  ]),
  title: PropTypes.string,
  body: PropTypes.string,
  image: PropTypes.string,
  stepLabel: PropTypes.string,
  isFirst: PropTypes.bool,
  isLast: PropTypes.bool,
  onPrev: PropTypes.func,
  onNext: PropTypes.func,
  onSkip: PropTypes.func,
};

export default GlobalHelperOverlay;
