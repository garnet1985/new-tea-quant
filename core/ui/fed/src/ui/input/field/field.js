import React, { useId } from 'react';
import HelpTooltip from 'ui/message/helpTooltip';
import { FIELD_LABEL_PLACEMENTS, pickToken } from 'ui/tokens';
import '../_control.scss';

/**
 * 表单字段壳：标签 above / inline / none + tip / hint / error。
 *
 * htmlFor:
 * - string：label[for] 指向该 id（须是 input/textarea/select/button 等可标注元素）
 * - ''：自动；优先用子控件已有 id
 * - false：不用 for，改走 aria-labelledby（RadioGroup 等组合控件）
 *
 * @example
 * <Field label="名称" tip="显示名">
 *   <input />
 * </Field>
 * <Field label="频率" htmlFor={false}>…</Field>
 */
function Field({
  label = '',
  labelPlacement = 'above',
  tip = '',
  hint = '',
  error = '',
  htmlFor = '',
  /** aria 模式下可传入，与 Select labelId 等对齐 */
  labelId: labelIdProp = '',
  required = false,
  /** 为 false 时不把 id clone 到子根节点（Select 等自行绑在真实控件上） */
  bindControlId = true,
  className = '',
  children,
}) {
  const autoId = useId().replace(/:/g, '');
  const placement = pickToken(labelPlacement, FIELD_LABEL_PLACEMENTS, 'above');
  const ariaLabelledBy = htmlFor === false;
  const childId = React.isValidElement(children) && children.props.id
    ? children.props.id
    : '';
  const controlId = ariaLabelledBy
    ? `ntq-${autoId}`
    : (htmlFor || childId || `ntq-${autoId}`);
  const labelId = labelIdProp || `${controlId}-label`;
  const showTextLabel = placement !== 'none' && Boolean(label);
  const showLabelRow = showTextLabel || Boolean(tip);
  const message = error || hint;
  const messageIsError = Boolean(error);

  let control = children;
  if (React.isValidElement(children) && (showTextLabel || message)) {
    const next = {
      'aria-invalid': error ? true : children.props['aria-invalid'],
      'aria-describedby': message
        ? [children.props['aria-describedby'], `${controlId}-msg`].filter(Boolean).join(' ')
        : children.props['aria-describedby'],
    };
    if (ariaLabelledBy && showTextLabel) {
      next['aria-labelledby'] = [labelId, children.props['aria-labelledby']]
        .filter(Boolean)
        .join(' ');
    } else if (bindControlId) {
      next.id = children.props.id || controlId;
    }
    control = React.cloneElement(children, next);
  }

  const rootClass = [
    'ntq-field',
    `ntq-field--${placement}`,
    error ? 'ntq-field--error' : '',
    className,
  ].filter(Boolean).join(' ');

  const labelNode = showLabelRow ? (
    <div className="ntq-field__label-row">
      {showTextLabel ? (
        ariaLabelledBy ? (
          <span id={labelId} className="ntq-field__label">
            {label}
            {required ? <span aria-hidden="true"> *</span> : null}
          </span>
        ) : (
          <label className="ntq-field__label" htmlFor={controlId}>
            {label}
            {required ? <span aria-hidden="true"> *</span> : null}
          </label>
        )
      ) : null}
      {tip ? <HelpTooltip title={tip} /> : null}
    </div>
  ) : null;

  const metaNode = message ? (
    <p
      id={`${controlId}-msg`}
      className={messageIsError ? 'ntq-field__error' : 'ntq-field__hint'}
      role={messageIsError ? 'alert' : undefined}
    >
      {message}
    </p>
  ) : null;

  if (placement === 'inline') {
    return (
      <div className={rootClass}>
        {labelNode}
        <div className="ntq-field__control">
          {control}
          {metaNode}
        </div>
      </div>
    );
  }

  return (
    <div className={rootClass}>
      {labelNode}
      <div className="ntq-field__control">{control}</div>
      {metaNode}
    </div>
  );
}

export default Field;
