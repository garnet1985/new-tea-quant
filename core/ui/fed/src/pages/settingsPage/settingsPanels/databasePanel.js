import React from 'react';
import {
  Heading,
  Loading,
  Message,
  Button,
  Section,
  Select as UiSelect,
  Text,
  TextField as UiTextField,
} from 'ui';

const DATABASE_TYPE_OPTIONS = [
  { value: 'duckdb', label: 'DuckDB（推荐，本地文件）' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
];

export function SettingsDatabasePanel({
  loading,
  loadError,
  saveError,
  saveOk,
  saving,
  databaseType,
  databaseName,
  duckdbDomains,
  onDatabaseTypeChange,
  onDatabaseNameChange,
  onSave,
  onReload,
}) {
  const isDuckdb = databaseType === 'duckdb';
  const domainEntries = Object.entries(duckdbDomains || {});

  if (loading) {
    return <Loading variant="inline" message="正在加载数据库配置…" />;
  }

  return (
    <Section className="settings-database" gap="lg">
      <Section className="settings-database__engine" gap="md">
        <Heading level="h3" gap="none">数据库引擎</Heading>
        <p className="ntq-muted">
          选择本机使用的数据库。DuckDB 为推荐的本地文件库；PostgreSQL / MySQL 还需在对应配置中填写连接信息。
        </p>
        {loadError ? <Message status="error">{loadError}</Message> : null}
        {saveError ? <Message status="error">{saveError}</Message> : null}
        {saveOk ? <Message status="success">{saveOk}</Message> : null}
        <UiSelect
          label="数据库类型"
          value={databaseType}
          onChange={(e) => onDatabaseTypeChange(e.target.value)}
          options={DATABASE_TYPE_OPTIONS}
        />
        {!isDuckdb ? (
          <UiTextField
            label="数据库名（库名）"
            value={databaseName}
            onChange={(e) => onDatabaseNameChange(e.target.value)}
            hint="仅允许字母、数字、下划线、连字符与点号。"
          />
        ) : null}
        <div className="settings-database__actions">
          <Button variant="primary" onClick={onSave} disabled={saving}>
            {saving ? '保存中…' : '保存数据库设置'}
          </Button>
          <Button
            variant="glass"
            icon="refresh"
            iconSize="sm"
            onClick={onReload}
            disabled={saving}
          >
            重新读取
          </Button>
        </div>
      </Section>

      {isDuckdb ? (
        <Section className="settings-database__duckdb" gap="md">
          <Heading level="h3" gap="none">DuckDB 数据域</Heading>
          <p className="ntq-muted">
            当前使用本地 DuckDB 文件库，按域拆分存储。
          </p>
          {domainEntries.length > 0 ? (
            <ul className="settings-database__domain-list">
              {domainEntries.map(([domain, path]) => (
                <li key={domain}>
                  <Text variant="code">{domain}</Text>
                  <span className="ntq-muted">：</span>
                  <Text variant="code">{path}</Text>
                </li>
              ))}
            </ul>
          ) : (
            <p className="ntq-muted">
              默认域：
              <Text variant="code">data.duckdb</Text>
              {' / '}
              <Text variant="code">tag.duckdb</Text>
              {' / '}
              <Text variant="code">strategy.duckdb</Text>
              （使用 core 默认配置）
            </p>
          )}
          <Message status="info">
            高级参数请在对应数据库配置中调整；保存引擎类型后，相关进程可能需要重启才生效。
          </Message>
        </Section>
      ) : (
        <Section className="settings-database__remote" gap="md">
          <Heading level="h3" gap="none">连接说明</Heading>
          <Message status="info">
            PostgreSQL / MySQL 的主机、端口与账号等请在对应引擎配置中填写；本页只保存引擎类型与库名。
          </Message>
        </Section>
      )}
    </Section>
  );
}
