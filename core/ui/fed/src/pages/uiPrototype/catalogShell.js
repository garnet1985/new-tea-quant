import React from 'react';
import { Box, Link as MuiLink } from '@mui/material';
import { Link as RouterLink, Outlet, useParams } from 'react-router-dom';
import Column from 'ui/layout/column';
import Block from 'ui/layout/block';
import Text from 'ui/text/text';
import Heading from 'ui/text/heading';
import { UI_CATALOG, UI_CATALOG_BASE, categoryPath } from './catalog';
import './uiPrototype.scss';

function UiPrototypeCatalogShell() {
  const { categoryId } = useParams();

  return (
    <Column
      className="ui-prototype"
      variant="sidebar"
      gap="none"
      divider="line"
      stack
    >
      <Block
        className="ui-prototype__sidebar"
        surface="panel"
        radius="none"
        padding="md"
        gap="sm"
      >
        <Heading level="h3" gap="none" className="ui-prototype__sidebar-title">
          UI 组件图鉴
        </Heading>
        <p className="ntq-caption ui-prototype__sidebar-hint">
          隐形页 ·
          {' '}
          <Text variant="code">{UI_CATALOG_BASE}</Text>
        </p>
        <Box component="nav" className="ui-prototype__menu" aria-label="组件大类">
          {UI_CATALOG.map((category) => {
            const active = category.id === categoryId;
            return (
              <MuiLink
                key={category.id}
                component={RouterLink}
                to={categoryPath(category.id)}
                underline="none"
                className={[
                  'ui-prototype__menu-item',
                  active ? 'is-active' : '',
                ].filter(Boolean).join(' ')}
              >
                <span className="ui-prototype__menu-label">{category.label}</span>
                <span className="ui-prototype__menu-count">{category.widgets.length}</span>
              </MuiLink>
            );
          })}
        </Box>
      </Block>
      <Box className="ui-prototype__content" component="main">
        <Outlet />
      </Box>
    </Column>
  );
}

export default UiPrototypeCatalogShell;
