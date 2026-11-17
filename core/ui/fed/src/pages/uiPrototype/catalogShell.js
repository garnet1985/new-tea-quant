import React, { useMemo } from 'react';
import { Box } from '@mui/material';
import { Outlet, useParams } from 'react-router-dom';
import Column from 'ui/layout/column';
import Block from 'ui/layout/block';
import SideNav from 'ui/layout/sideNav';
import Text from 'ui/text/text';
import Heading from 'ui/text/heading';
import { UI_CATALOG, UI_CATALOG_BASE, categoryPath } from './catalog';
import './uiPrototype.scss';

function UiPrototypeCatalogShell() {
  const { categoryId } = useParams();

  const navItems = useMemo(
    () => UI_CATALOG.map((category) => ({
      id: category.id,
      label: category.label,
      to: categoryPath(category.id),
      meta: category.widgets.length,
    })),
    [],
  );

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
        <SideNav
          variant="line"
          activeId={categoryId || ''}
          items={navItems}
          aria-label="组件大类"
        />
      </Block>
      <Box className="ui-prototype__content" component="main">
        <Outlet />
      </Box>
    </Column>
  );
}

export default UiPrototypeCatalogShell;
