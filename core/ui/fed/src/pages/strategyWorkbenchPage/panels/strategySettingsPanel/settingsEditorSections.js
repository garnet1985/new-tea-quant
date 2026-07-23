import React, { useCallback, useMemo } from 'react';
import Editor from 'components/editor/editor';
import strategyGoalSchema from './editorSchemas/strategyGoal';
import {
  applyGoalActions,
  normalizeGoalSettings,
} from './editorSchemas/strategyGoal';
import {
  cleanupSamplingByStrategy,
  normalizeSamplingSettings,
} from './editorSchemas/strategySampling';
import {
  cleanupSimulationByTemplate,
  resolveSimulationDisplayValue,
} from './editorSchemas/strategySimulation';

const editorAreEqual = (prev, next) => (
  prev.schema === next.schema
  && prev.value === next.value
  && prev.onChange === next.onChange
  && prev.context === next.context
  && prev.errors === next.errors
  && prev.onValidate === next.onValidate
  && prev.onValidationChange === next.onValidationChange
);

const MemoEditor = React.memo(function MemoEditor(props) {
  return <Editor {...props} />;
}, editorAreEqual);

export const GoalSettingsEditor = React.memo(function GoalSettingsEditor({
  goal,
  onGoalChange,
  context,
}) {
  const value = useMemo(() => normalizeGoalSettings(goal), [goal]);
  const handleChange = useCallback(
    (nextValue) => onGoalChange(applyGoalActions(nextValue || {})),
    [onGoalChange],
  );

  return (
    <MemoEditor
      schema={strategyGoalSchema}
      value={value}
      onChange={handleChange}
      context={context}
    />
  );
});

export const SimulationSettingsEditor = React.memo(function SimulationSettingsEditor({
  simulation,
  onSimulationChange,
  context,
  schema,
  simulationTemplateProfiles = {},
  errors,
  onValidate,
  onValidationChange,
}) {
  const value = useMemo(
    () => resolveSimulationDisplayValue(simulation, simulationTemplateProfiles),
    [simulation, simulationTemplateProfiles],
  );
  const handleChange = useCallback(
    (nextValue) => onSimulationChange(cleanupSimulationByTemplate(nextValue)),
    [onSimulationChange],
  );

  return (
    <MemoEditor
      schema={schema}
      value={value}
      onChange={handleChange}
      errors={errors}
      onValidate={onValidate}
      onValidationChange={onValidationChange}
      context={context}
    />
  );
});

export const SamplingSettingsEditor = React.memo(function SamplingSettingsEditor({
  sampling,
  onSamplingChange,
  context,
  schema,
}) {
  const value = useMemo(() => normalizeSamplingSettings(sampling), [sampling]);
  const handleChange = useCallback(
    (nextValue) => onSamplingChange(cleanupSamplingByStrategy(nextValue)),
    [onSamplingChange],
  );

  return (
    <MemoEditor
      schema={schema}
      value={value}
      onChange={handleChange}
      context={context}
    />
  );
});

export const SettingsSchemaEditor = React.memo(function SettingsSchemaEditor({
  schema,
  value,
  onChange,
  context,
}) {
  return (
    <MemoEditor
      schema={schema}
      value={value}
      onChange={onChange}
      context={context}
    />
  );
});
