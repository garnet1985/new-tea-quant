import React from 'react';
import PropTypes from 'prop-types';
import { Button } from 'ui';
import { renderHelpRichText } from './helpRichText';
import './style.scss';

/**
 * 页面引导遮罩卡：可挖洞聚焦，或无 target 时全屏 dim。
 * 末页只显示「我知道了」；有后续时显示「下一页」（不另放「跳过」）。
 */
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
  onClose = () => {},
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
          <Button
            variant="ghost"
            icon="close"
            className="ntq-global-helper__close"
            onClick={onClose}
            aria-label="关闭引导"
          />
        </div>
        {title ? (
          <h2 className="ntq-global-helper__title">{renderHelpRichText(title)}</h2>
        ) : null}
        {body ? (
          <p className="ntq-global-helper__body">{renderHelpRichText(body)}</p>
        ) : null}
        {image ? (
          <img className="ntq-global-helper__image" src={image} alt="" />
        ) : null}
        <div className="ntq-global-helper__actions">
          <div className="ntq-global-helper__nav">
            {!isFirst ? (
              <Button
                variant="glass"
                className="ntq-global-helper__prev"
                onClick={onPrev}
              >
                上一步
              </Button>
            ) : null}
            {isLast ? (
              <Button
                variant="primary"
                className="ntq-global-helper__done"
                onClick={onNext}
              >
                我知道了
              </Button>
            ) : (
              <Button
                variant="primary"
                className="ntq-global-helper__next"
                onClick={onNext}
              >
                下一页
              </Button>
            )}
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
  title: PropTypes.node,
  body: PropTypes.node,
  image: PropTypes.string,
  stepLabel: PropTypes.string,
  isFirst: PropTypes.bool,
  isLast: PropTypes.bool,
  onPrev: PropTypes.func,
  onNext: PropTypes.func,
  onClose: PropTypes.func,
};

export default GlobalHelperOverlay;
